from __future__ import annotations

import argparse
import asyncio

from pydantic import BaseModel

from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.vault.vault_repository import VaultRepository

from personal_secret.api.infrastructure.crypto.cache import session_cache
from personal_secret.api.infrastructure.postgresql.client import db_client
from personal_secret.api.infrastructure.postgresql.session import transactional_session


# #
# input

class Input(BaseModel):
    pass


# #
# usecase

@typecheck
async def status(*, session, input: Input) -> dict:
    # 초기화 여부(DB) + unlock 여부(세션 캐시)
    vault = await VaultRepository.get(session=session)
    return {
        "data": {
            "initialized": vault is not None,
            "unlocked": session_cache.is_unlocked(),
        }
    }


# #
# cli

def _parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser().parse_args()

async def _main():
    _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(await status(session=session, input=Input()))

if __name__ == "__main__":
    asyncio.run(_main())
