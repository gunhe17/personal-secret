from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime

from pydantic import BaseModel

from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.common.exception import AlreadyExistsError
from personal_secret.api.domain.secret.secret import Secret
from personal_secret.api.domain.secret.kind import Kind
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
    kind: str
    name: str
    tags: list[str] = []
    expires_at: datetime | None = None
    data: dict


# #
# usecase

@typecheck
async def create(*, session, input: Input) -> dict:

    if await SecretRepository.exists_by_name(
        session=session,
        name=Name.from_str(input.name),
    ):
        raise AlreadyExistsError("Secret", input.name)

    # persist
    event, entity = SecretEvent.created(
        secret=(
            await SecretRepository.add(
                session=session,
                entity=Secret.new(
                    kind=Kind.from_str(input.kind),
                    name=Name.from_str(input.name),
                    tags=Tags.from_list(input.tags),
                    ciphertext=Ciphertext.from_bytes(
                        bytes=session_cache.encrypt(
                            plaintext=json.dumps(input.data).encode("utf-8"),
                        )
                    ),
                    expires_at=(
                        ExpiresAt.from_datetime(input.expires_at) if input.expires_at else None
                    ),
                ),
            )
        )
    )

    return {
        "data": entity.to_dict(),
        "event": [
            event.to_dict()
            for event in (await EventRepository.emit(session=session, events=[event]))
        ]
    }


# #
# cli

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--tags", nargs="*", default=[])
    parser.add_argument("--expires-at", default=None)
    parser.add_argument("--data", required=True)
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(await create(
            session=session,
            input=Input(
                kind=args.kind,
                name=args.name,
                tags=args.tags,
                expires_at=args.expires_at,
                data=json.loads(args.data),
            ),
        ))

if __name__ == "__main__":
    asyncio.run(_main())
