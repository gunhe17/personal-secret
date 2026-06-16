from __future__ import annotations

import argparse
import asyncio

from pydantic import BaseModel

from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.account.email import Email
from personal_secret.api.domain.account.account_repository import AccountRepository
from personal_secret.api.domain.account.account_event import AccountEvent

from personal_secret.api.domain.event.event_repository import EventRepository

from personal_secret.api.infrastructure.postgresql.client import db_client
from personal_secret.api.infrastructure.postgresql.session import transactional_session


# #
# input

class Input(BaseModel):
    email: str


# #
# usecase

@typecheck
async def get_only_salts(*, session, input: Input) -> dict:
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
    )

    # return
    return {
        "data": {
            "personal_unlock_salt": account.personal_unlock_salt.to_str(),
            "login_salt": account.login_salt.to_str(),
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
            await get_only_salts(
                session=session,
                input=Input(email=args.email),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
