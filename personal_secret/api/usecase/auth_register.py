from __future__ import annotations

import argparse
import asyncio

from pydantic import BaseModel

from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.account.account import Account
from personal_secret.api.domain.account.email import Email
from personal_secret.api.domain.account.personal_lock import PersonalLock
from personal_secret.api.domain.account.personal_locked_key import PersonalLockedKey
from personal_secret.api.domain.account.personal_unlock_salt import PersonalUnlockSalt
from personal_secret.api.domain.account.login_salt import LoginSalt
from personal_secret.api.domain.account.login_verifier import LoginVerifier
from personal_secret.api.domain.account.account_repository import AccountRepository
from personal_secret.api.domain.account.account_event import AccountEvent

from personal_secret.api.domain.event.event_repository import EventRepository

from personal_secret.api.infrastructure.crypto.client import crypto
from personal_secret.api.infrastructure.postgresql.client import db_client
from personal_secret.api.infrastructure.postgresql.session import transactional_session


# #
# input

class Input(BaseModel):
    email: str
    personal_lock: str
    personal_locked_key: str
    personal_unlock_salt: str
    login_salt: str
    login_proof: str


# #
# usecase

@typecheck
async def register(*, session, input: Input) -> dict:
    # persist
    event, account = AccountEvent.created(
        account=await AccountRepository.add_unique_by_email(
            session=session,
            entity=Account.new(
                email=Email.from_str(input.email),
                personal_lock=PersonalLock.from_str(input.personal_lock),
                personal_locked_key=PersonalLockedKey.from_str(input.personal_locked_key),
                personal_unlock_salt=PersonalUnlockSalt.from_str(input.personal_unlock_salt),
                login_salt=LoginSalt.from_str(input.login_salt),
                login_verifier=LoginVerifier.from_str(
                    crypto.hash_password(password=input.login_proof),
                ),
            ),
        ),
    )

    # return
    return {
        "data": account.to_dict(),
        "event": [
            event.to_dict()
            for event in (
                await EventRepository.emit(
                    session=session,
                    events=[event],
                )
            )
        ],
    }


# #
# cli

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--personal-lock", required=True)
    parser.add_argument("--personal-locked-key", required=True)
    parser.add_argument("--personal-unlock-salt", required=True)
    parser.add_argument("--login-salt", required=True)
    parser.add_argument("--login-proof", required=True)
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await register(
                session=session,
                input=Input(
                    email=args.email,
                    personal_lock=args.personal_lock,
                    personal_locked_key=args.personal_locked_key,
                    personal_unlock_salt=args.personal_unlock_salt,
                    login_salt=args.login_salt,
                    login_proof=args.login_proof,
                ),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
