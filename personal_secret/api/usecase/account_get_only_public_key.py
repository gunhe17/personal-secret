from __future__ import annotations

import argparse
import asyncio
from uuid import UUID

from pydantic import BaseModel

from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.account.email import Email
from personal_secret.api.domain.account.account_repository import AccountRepository
from personal_secret.api.domain.account.account_event import AccountEvent

from personal_secret.api.domain.event.event_repository import EventRepository

from personal_secret.api.infrastructure.database.postgresql.client import db_client
from personal_secret.api.infrastructure.database.common.session import transactional_session


# #
# input

class Input(BaseModel):
    email: str


# #
# usecase

@typecheck
async def get_only_public_key(*, session, input: Input, actor_id: UUID | None = None) -> dict:
    # find
    event, account = AccountEvent.read(
        account=(
            await AccountRepository.get_by_email(
                session=session,
                email=Email.from_str(input.email),
            )
        )
    )

    # emit
    await EventRepository.emit(
        session=session,
        events=[event],
        actor_id=actor_id,
    )

    # return
    return {
        "data": {
            "account_id": str(account.id),
            "personal_lock": account.personal_lock.to_str(),
        },
    }


# #
# cli

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await get_only_public_key(
                session=session,
                input=Input(email=args.email),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
