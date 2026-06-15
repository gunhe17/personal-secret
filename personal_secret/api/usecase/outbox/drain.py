from __future__ import annotations

import argparse
import asyncio

from pydantic import BaseModel

from personal_secret.api.core.validate import typecheck

from personal_secret.api.config import get_outbox_config

from personal_secret.api.domain.event.event_repository import EventRepository

from personal_secret.api.infrastructure.outbox.handler import dispatch
from personal_secret.api.infrastructure.postgresql.client import db_client
from personal_secret.api.infrastructure.postgresql.session import transactional_session


# #
# input

class Input(BaseModel):
    pass


# #
# usecase

@typecheck
async def drain(*, session, input: Input) -> dict:
    config = get_outbox_config()

    # claim
    events = await EventRepository.claim_pending(
        session=session,
        limit=config.OUTBOX_BATCH_SIZE,
    )

    # dispatch
    succeeded, failed = 0, 0
    for event in events:
        try:
            dispatch(event=event.to_dict())
        except Exception as exc:
            await EventRepository.fail(session=session, event=event, error=str(exc))
            failed += 1
            continue
        await EventRepository.succeed(session=session, event=event)
        succeeded += 1

    # return
    return {
        "claimed": len(events),
        "succeeded": succeeded,
        "failed": failed,
    }


# #
# cli

def _parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser().parse_args()

async def _main():
    _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await drain(
                session=session,
                input=Input(),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
