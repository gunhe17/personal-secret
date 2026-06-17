from __future__ import annotations

import argparse
import asyncio
from uuid import UUID

from pydantic import BaseModel

from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.secret.secret_repository import SecretRepository
from personal_secret.api.domain.secret.secret_event import SecretEvent

from personal_secret.api.domain.event.event_repository import EventRepository

from personal_secret.api.infrastructure.database.postgresql.client import db_client
from personal_secret.api.infrastructure.database.common.session import transactional_session


# #
# input

class Input(BaseModel):
    id: str


# #
# usecase

@typecheck
async def reveal(*, session, input: Input, team_id: UUID, actor_id: UUID | None = None) -> dict:
    # find
    event, secret = SecretEvent.read(
        secret=(
            await SecretRepository.get_by_id(
                session=session,
                id=UUID(input.id),
                team_id=team_id,
            )
        )
    )

    # emit
    await EventRepository.emit(
        session=session,
        events=[event],
        actor_id=actor_id,
        actor_team_id=team_id,
    )

    # return
    return {
        "data": {**secret.to_dict(), "value": secret.value.to_str()},
    }


# #
# cli

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("id")
    parser.add_argument("--team-id", required=True)
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await reveal(
                session=session,
                input=Input(id=args.id),
                team_id=UUID(args.team_id),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
