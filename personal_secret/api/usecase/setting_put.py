from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any
from uuid import uuid4

from personal_secret.api.core.usecase import In
from personal_secret.api.core.usecase import Out
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.setting.key import Key
from personal_secret.api.domain.setting.value import Value
from personal_secret.api.domain.setting.setting_repository import SettingRepository
from personal_secret.api.domain.setting.setting_event import SettingEvent

from personal_secret.api.domain.event.event.event_repository import EventRepository

from personal_secret.api.infrastructure.database.postgresql.client import db_client
from personal_secret.api.infrastructure.database.common.session import transactional_session


# #
# input

class Input(In):
    key: str
    value: Any


# #
# output

class Output(Out):
    pass


# #
# usecase

@typecheck
async def put(*, session, event_group_id, input: Input) -> Output:
    # set
    event, setting = SettingEvent.updated(
        setting=(
            await SettingRepository.set_by_key(
                session=session,
                key=Key.from_str(input.key),
                value=Value.from_json(input.value),
            )
        )
    )

    # return
    return Output(
        data=setting.to_dict(),
        event=[
            e.to_dict()
            for e in (
                await EventRepository.emit(
                    session=session,
                    id=event_group_id,
                    name="setting_put",
                    atomics=[event],
                )
            )
        ],
    )


# #
# cli

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("key")
    parser.add_argument("--value", required=True)
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await put(
                session=session,
                event_group_id=uuid4(),
                input=Input(key=args.key, value=json.loads(args.value)),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
