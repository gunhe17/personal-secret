from __future__ import annotations

import argparse
import asyncio

from pydantic import BaseModel

from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.common.exception import NotFoundError
from personal_secret.api.domain.secret.secret_repository import SecretRepository
from personal_secret.api.domain.secret.secret_event import SecretEvent

from personal_secret.api.domain.event.event_repository import EventRepository

from personal_secret.api.infrastructure.postgresql.client import db_client
from personal_secret.api.infrastructure.postgresql.session import transactional_session


# #
# input

class Input(BaseModel):
    identifier: str


# #
# usecase

@typecheck
async def delete(*, session, input: Input) -> dict:
    # load
    secret = await SecretRepository.find_by_identifier(session=session, identifier=input.identifier)
    if secret is None:
        raise NotFoundError("Secret", input.identifier)

    # event(삭제) — soft-delete + 마커 한 덩어리 → 저장 + 응답
    event, removed = SecretEvent.deleted(
        secret=await SecretRepository.remove_by_id(
            session=session, 
            id=secret.id
        ),
    )
    
    return {
        "data": removed.to_dict(),
        "event": [
            event.to_dict()
            for event in (await EventRepository.emit(session=session, events=[event]))
        ]
    }


# #
# cli

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("identifier")
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(await delete(
            session=session,
            input=Input(identifier=args.identifier),
        ))

if __name__ == "__main__":
    asyncio.run(_main())
