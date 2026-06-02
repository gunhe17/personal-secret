from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime

from pydantic import BaseModel

from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.common.exception import AlreadyExistsError, NotFoundError
from personal_secret.api.domain.secret.name import Name
from personal_secret.api.domain.secret.tags import Tags
from personal_secret.api.domain.secret.expires_at import ExpiresAt
from personal_secret.api.domain.secret.ciphertext import Ciphertext
from personal_secret.api.domain.secret.secret_repository import SecretRepository
from personal_secret.api.domain.secret.secret_event import SecretEvent

from personal_secret.api.domain.event.event_repository import EventRepository

from personal_secret.api.infrastructure.crypto.cache import session_cache
from personal_secret.api.infrastructure.postgresql.client import db_client
from personal_secret.api.infrastructure.postgresql.session import transactional_session


# #
# input

class Input(BaseModel):
    identifier: str
    name: str | None = None
    tags: list[str] | None = None
    expires_at: datetime | None = None
    data: dict | None = None


# #
# usecase

@typecheck
async def update(*, session, input: Input) -> dict:
    # load
    secret = await SecretRepository.find_by_identifier(session=session, identifier=input.identifier)
    if secret is None:
        raise NotFoundError("Secret", input.identifier)

    # rename guard (name 제공 시에만)
    if input.name is not None:
        name = Name.from_str(input.name)
        clash = await SecretRepository.find_by_name(session=session, name=name)
        if clash is not None and clash.id != secret.id:
            raise AlreadyExistsError("Secret", input.name)
    else:
        name = secret.name

    # metadata (생략된 필드는 기존값 보존 — None = 미변경)
    secret = secret.with_metadata(
        name=name,
        tags=Tags.from_list(input.tags) if input.tags is not None else secret.tags,
        expires_at=(
            ExpiresAt.from_datetime(input.expires_at) if input.expires_at is not None else secret.expires_at
        ),
    )

    # data (제공 시에만 재암호화)
    if input.data is not None:
        secret = secret.with_ciphertext(
            Ciphertext.from_bytes(
                bytes=session_cache.encrypt(plaintext=json.dumps(input.data).encode("utf-8")),
            )
        )

    # persist (load~update 사이 삭제 race → None)
    secret = await SecretRepository.update(session=session, entity=secret)
    if secret is None:
        raise NotFoundError("Secret", input.identifier)

    # event(수정) → 저장 + 응답 조합
    return {
        "data": secret.to_dict(),
        "event": [
            event.to_dict()
            for event in (await EventRepository.emit(session=session, events=[SecretEvent.updated(secret=secret)]))
        ]
    }


# #
# cli

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("identifier")
    parser.add_argument("--name", default=None)
    parser.add_argument("--tags", nargs="*", default=None)
    parser.add_argument("--expires-at", default=None)
    parser.add_argument("--data", default=None)
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(await update(
            session=session,
            input=Input(
                identifier=args.identifier,
                name=args.name,
                tags=args.tags,
                expires_at=args.expires_at,
                data=json.loads(args.data) if args.data else None,
            ),
        ))

if __name__ == "__main__":
    asyncio.run(_main())
