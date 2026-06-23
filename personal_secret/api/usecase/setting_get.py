from __future__ import annotations

import argparse
import asyncio
from uuid import UUID, uuid4

from personal_secret.api.core.usecase import In
from personal_secret.api.core.usecase import Out
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.setting.key import Key
from personal_secret.api.domain.setting.setting_repository import SettingRepository
from personal_secret.api.domain.setting.setting_event import SettingEvent

from personal_secret.api.domain.event.event.event_repository import EventRepository

from personal_secret.api.infrastructure.database.postgresql.client import db_client
from personal_secret.api.infrastructure.database.common.session import transactional_session


# #
# input

class Input(In):
    key: str


# #
# output

class Output(Out):
    pass


# #
# usecase

@typecheck
async def get(*, session, event_group_id, input: Input, account_id: UUID | None = None) -> Output:
    # find
    event, setting = SettingEvent.read(
        setting=(
            await SettingRepository.get_by_key(
                session=session,
                key=Key.from_str(input.key),
            )
        )
    )

    # return
    return Output(
        data=setting.to_dict(),
        event=[
            event.to_dict()
            for event in (
                await EventRepository.emit(
                    session=session,
                    id=event_group_id,
                    name="setting_get",
                    atomics=[event],
                    actor_id=account_id,
                )
            )
        ],
    )


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
                event_group_id=uuid4(),
                input=Input(key=args.key),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
