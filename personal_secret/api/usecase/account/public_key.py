from __future__ import annotations

import argparse
import asyncio

from pydantic import BaseModel

from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.common.exception import NotFoundError

from personal_secret.api.domain.account.email import Email
from personal_secret.api.domain.account.account_repository import AccountRepository

from personal_secret.api.infrastructure.postgresql.client import db_client
from personal_secret.api.infrastructure.postgresql.session import transactional_session


# #
# input

class Input(BaseModel):
    email: str


# #
# usecase

@typecheck
async def public_key(*, session, input: Input) -> dict:
    # 초대자가 상대 personal_lock 으로 team_key 를 봉인하려면 공개키가 필요
    account = await AccountRepository.find_by_email(
        session=session,
        email=Email.from_str(input.email),
    )
    if account is None:
        raise NotFoundError("Account", input.email)

    # return
    return {
        "data": {
            "account_id": str(account.id),
            "personal_lock": account.personal_lock.to_str(),
        }
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
            await public_key(
                session=session,
                input=Input(email=args.email),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
