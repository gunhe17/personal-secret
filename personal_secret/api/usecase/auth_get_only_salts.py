from __future__ import annotations

import argparse
import asyncio

from personal_secret.api.core.usecase import In
from personal_secret.api.core.usecase import Out
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.account.email import Email
from personal_secret.api.domain.account.account_repository import AccountRepository
from personal_secret.api.domain.account.account_event import AccountEvent

from personal_secret.api.domain.event.event_repository import EventRepository

from personal_secret.api.infrastructure.database.postgresql.client import db_client
from personal_secret.api.infrastructure.database.common.session import transactional_session


# #
# input

class Input(In):
    email: str


# #
# output

class Output(Out):
    pass


# #
# usecase

@typecheck
async def get_only_salts(*, session, input: Input) -> Output:
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
    return Output.new(
        data={
            "personal_unlock_salt": account.personal_unlock_salt.to_str(),
            "login_salt": account.login_salt.to_str(),
        },
        event=None,
    )


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
