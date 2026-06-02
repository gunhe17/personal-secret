from __future__ import annotations

import argparse
import asyncio
import json

from pydantic import BaseModel

from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.common.exception import NotFoundError
from personal_secret.api.domain.secret.secret_repository import SecretRepository

from personal_secret.api.infrastructure.crypto.cache import session_cache
from personal_secret.api.infrastructure.postgresql.client import db_client
from personal_secret.api.infrastructure.postgresql.session import transactional_session


# #
# input

class Input(BaseModel):
    identifier: str


# #
# usecase

@typecheck
async def reveal(*, session, input: Input) -> dict:
    # load
    secret = await SecretRepository.find_by_identifier(session=session, identifier=input.identifier)
    if secret is None:
        raise NotFoundError("Secret", input.identifier)

    # decrypt (session_cache가 DEK·lock·복호화 처리, 잠겨있으면 LockedError)
    plaintext = session_cache.decrypt(data=secret.ciphertext.to_bytes())
    data = json.loads(plaintext.decode("utf-8"))

    revealed = {**secret.to_dict(), "data": data}
    return revealed


# #
# cli

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("identifier")
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(await reveal(
            session=session,
            input=Input(identifier=args.identifier),
        ))

if __name__ == "__main__":
    asyncio.run(_main())
