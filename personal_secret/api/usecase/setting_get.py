from __future__ import annotations

import argparse
import asyncio
from uuid import UUID

from pydantic import BaseModel

from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.setting.key import Key
from personal_secret.api.domain.setting.setting_repository import SettingRepository
from personal_secret.api.domain.setting.setting_event import SettingEvent

from personal_secret.api.domain.event.event_repository import EventRepository

from personal_secret.api.infrastructure.database.postgresql.client import db_client
from personal_secret.api.infrastructure.database.common.session import transactional_session


# #
# input

class Input(BaseModel):
    key: str


# #
# usecase

@typecheck
async def get(*, session, input: Input, actor_id: UUID | None = None) -> dict:
    # find
    event, setting = SettingEvent.read(
        setting=(
            await SettingRepository.get_by_key(
                session=session,
                key=Key.from_str(input.key),
            )
        )
    )

    # emit
    await EventRepository.emit(
        session=session,
        events=[event],
        actor_id=actor_id,
    )

    # return
    return {
        "data": setting.to_dict(),
    }


# #
# cli

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("key")
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await get(
                session=session,
                input=Input(key=args.key),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
