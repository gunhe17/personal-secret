from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from personal_secret.api.core.usecase import In
from personal_secret.api.core.usecase import Out
from personal_secret.api.core.validate import typecheck

from personal_secret.api.config import get_auth_config

from personal_secret.api.domain.common.exception import InvalidCredentialError

from personal_secret.api.domain.account.email import Email
from personal_secret.api.domain.account.account_repository import AccountRepository

from personal_secret.api.domain.account_token.account_token import AccountToken
from personal_secret.api.domain.account_token.fingerprint import Fingerprint
from personal_secret.api.domain.account_token.expires_at import ExpiresAt
from personal_secret.api.domain.account_token.account_token_repository import AccountTokenRepository
from personal_secret.api.domain.account_token.account_token_event import AccountTokenEvent

from personal_secret.api.domain.event.event.event_repository import EventRepository

from personal_secret.api.infrastructure.hash.argon2.client import argon2
from personal_secret.api.infrastructure.hash.sha256.client import sha256
from personal_secret.api.infrastructure.token.secrets.client import token
from personal_secret.api.infrastructure.database.postgresql.client import db_client
from personal_secret.api.infrastructure.database.common.session import transactional_session


# #
# input

class Input(In):
    email: str
    login_proof: str


# #
# output

class Output(Out):
    pass


# #
# usecase

@typecheck
async def login(*, session, event_group_id, input: Input) -> Output:
    # find
    account = await AccountRepository.verify_email(
        session=session,
        email=Email.from_str(input.email),
    )

    # verify
    if not (
        argon2.verify(
            hash=account.login_verifier.to_str(),
            value=input.login_proof,
        )
    ):
        raise InvalidCredentialError()

    # issue
    raw_token = token.generate()

    event, issued = AccountTokenEvent.created(
        account_token=await AccountTokenRepository.add(
            session=session,
            entity=AccountToken.new(
                account_id=account.id,
                fingerprint=Fingerprint.from_str(
                    sha256.hash(value=raw_token)
                ),
                expires_at=ExpiresAt.from_datetime(
                    datetime.now(timezone.utc) + timedelta(seconds=get_auth_config().TOKEN_TTL_SEC)
                ),
            ),
        ),
    )

    # return
    return Output(
        data={
            "token": raw_token,
            "expires_at": issued.expires_at.to_str(),
            **account.to_keys(),
        },
        event=[
            event.to_dict()
            for event in (
                await EventRepository.emit(
                    session=session,
                    id=event_group_id,
                    name="auth_login",
                    atomics=[event],
                    actor_id=account.id,
                )
            )
        ],
    )


# #
# cli

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--login-proof", required=True)
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await login(
                session=session,
                event_group_id=uuid4(),
                input=Input(email=args.email, login_proof=args.login_proof),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
