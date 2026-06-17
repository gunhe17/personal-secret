from __future__ import annotations

import argparse
import asyncio
from uuid import UUID

from pydantic import BaseModel

from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.setting.setting_repository import SettingRepository
from personal_secret.api.domain.setting.setting_event import SettingEvent

from personal_secret.api.domain.event.event_repository import EventRepository

from personal_secret.api.infrastructure.database.postgresql.client import db_client
from personal_secret.api.infrastructure.database.common.session import transactional_session


# #
# input

class Input(BaseModel):
    limit: int | None = None
    offset: int | None = None


# #
# usecase

@typecheck
async def list_settings(*, session, input: Input, actor_id: UUID | None = None) -> dict:
    # find
    founds = SettingEvent.read_many(
        settings=(
            await SettingRepository.list_all(
                session=session,
                limit=input.limit,
                offset=input.offset,
            )
        )
    )

    # emit
    await EventRepository.emit(
        session=session,
        events=[event for event, _ in founds],
        actor_id=actor_id,
    )

    # return
    return {
        "data": [setting.to_dict() for _, setting in founds],
    }


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
