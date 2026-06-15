from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel

from personal_secret.api.core.validate import typecheck

from personal_secret.api.config import get_auth_config

from personal_secret.api.domain.common.exception import InvalidCredentialError

from personal_secret.api.domain.account.email import Email
from personal_secret.api.domain.account.account_repository import AccountRepository

from personal_secret.api.domain.token.token import Token
from personal_secret.api.domain.token.fingerprint import Fingerprint
from personal_secret.api.domain.token.expires_at import ExpiresAt
from personal_secret.api.domain.token.token_repository import TokenRepository

from personal_secret.api.infrastructure.crypto.client import crypto
from personal_secret.api.infrastructure.postgresql.client import db_client
from personal_secret.api.infrastructure.postgresql.session import transactional_session


# #
# input

class Input(BaseModel):
    email: str
    login_proof: str


# #
# usecase

@typecheck
async def login(*, session, input: Input) -> dict:
    # find (이메일/증명 어느쪽 오류인지 구분 노출 안 함)
    account = await AccountRepository.find_by_email(
        session=session,
        email=Email.from_str(input.email),
    )
    if account is None:
        raise InvalidCredentialError()

    # verify
    if not crypto.verify_password(hash=account.login_verifier.to_str(), password=input.login_proof):
        raise InvalidCredentialError()

    # issue
    raw = crypto.generate_token()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=get_auth_config().TOKEN_TTL_SEC)
    token = await TokenRepository.add(
        session=session,
        entity=Token.new(
            account_id=account.id,
            fingerprint=Fingerprint.from_str(crypto.hash_token(token=raw)),
            expires_at=ExpiresAt.from_datetime(expires_at),
        ),
    )

    # return
    return {
        "data": {
            "token": raw,
            "expires_at": token.expires_at.to_str(),
            **account.to_keys(),
        }
    }


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
                input=Input(email=args.email, login_proof=args.login_proof),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
