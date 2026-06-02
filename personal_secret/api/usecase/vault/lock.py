from __future__ import annotations

import argparse
import asyncio

from pydantic import BaseModel

from personal_secret.api.core.validate import typecheck

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
async def lock(*, session, input: Input) -> dict:
    # 세션 DEK 폐기 (in-memory, DB 변경 없음 → 이벤트 없음)
    session_cache.lock()
    return {"data": {"unlocked": False}}


# #
# cli

def _parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser().parse_args()

async def _main():
    _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(await lock(session=session, input=Input()))

if __name__ == "__main__":
    asyncio.run(_main())
