from __future__ import annotations

import argparse
import asyncio
from uuid import UUID

from pydantic import BaseModel

from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.account_team.account_team_repository import AccountTeamRepository
from personal_secret.api.domain.account_team.account_team_event import AccountTeamEvent

from personal_secret.api.domain.event.event_repository import EventRepository

from personal_secret.api.infrastructure.database.postgresql.client import db_client
from personal_secret.api.infrastructure.database.common.session import transactional_session


# #
# input

class Input(BaseModel):
    pass


# #
# usecase

@typecheck
async def get_only_key(*, session, input: Input, team_id: UUID, actor_id: UUID) -> dict:
    # find
    event, membership = AccountTeamEvent.read(
        membership=(
            await AccountTeamRepository.get_by_account_and_team(
                session=session,
                account_id=actor_id,
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
        "data": membership.to_keys(),
    }


# #
# cli

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--team-id", required=True)
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await get_only_key(
                session=session,
                input=Input(),
                team_id=UUID(args.team_id),
                actor_id=UUID(args.account_id),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
