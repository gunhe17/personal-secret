from __future__ import annotations

import argparse
import asyncio

from pydantic import BaseModel

from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.setting.setting_repository import SettingRepository

from personal_secret.api.infrastructure.postgresql.client import db_client
from personal_secret.api.infrastructure.postgresql.session import transactional_session


# #
# input

class Input(BaseModel):
    limit: int | None = None
    offset: int | None = None


# #
# usecase

@typecheck
async def list_settings(*, session, input: Input) -> list[dict]:
    # find
    settings = await SettingRepository.list_all(session=session, limit=input.limit, offset=input.offset)

    # return
    return [
        s.to_dict() for s in settings
    ]


# #
# cli

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--offset", type=int, default=None)
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await list_settings(
                session=session,
                input=Input(limit=args.limit, offset=args.offset),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
