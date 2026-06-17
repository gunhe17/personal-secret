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
    account_id: str


# #
# usecase

@typecheck
async def remove(*, session, input: Input, team_id: UUID, actor_id: UUID | None = None) -> dict:
    # remove
    event, removed = AccountTeamEvent.deleted(
        membership=(
            await AccountTeamRepository.remove_by_account_and_team(
                session=session,
                account_id=UUID(input.account_id),
                team_id=team_id,
            )
        )
    )

    # return
    return {
        "data": removed.to_dict(),
        "event": [
            event.to_dict()
            for event in (
                await EventRepository.emit(
                    session=session,
                    events=[event],
                    actor_id=actor_id,
                    actor_team_id=team_id,
                )
            )
        ],
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
            await remove(
                session=session,
                input=Input(account_id=args.account_id),
                team_id=UUID(args.team_id),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
