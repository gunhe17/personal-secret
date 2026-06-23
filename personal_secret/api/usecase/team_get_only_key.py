from __future__ import annotations

import argparse
import asyncio
from uuid import UUID, uuid4

from personal_secret.api.core.usecase import In
from personal_secret.api.core.usecase import Out
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.team_access.team_access_repository import TeamAccessRepository
from personal_secret.api.domain.team_access.team_access_event import TeamAccessEvent

from personal_secret.api.domain.event.event.event_repository import EventRepository

from personal_secret.api.infrastructure.database.postgresql.client import db_client
from personal_secret.api.infrastructure.database.common.session import transactional_session


# #
# input

class Input(In):
    pass


# #
# output

class Output(Out):
    pass


# #
# usecase

@typecheck
async def get_only_key(*, session, event_group_id, input: Input, team_id: UUID, account_id: UUID) -> Output:
    # find
    event, team_access = TeamAccessEvent.read(
        team_access=(
            await TeamAccessRepository.get_by_account_and_team(
                session=session,
                account_id=account_id,
                team_id=team_id,
            )
        )
    )

    # return
    return Output(
        data=team_access.to_keys(),
        event=[
            event.to_dict()
            for event in (
                await EventRepository.emit(
                    session=session,
                    id=event_group_id,
                    name="team_get_only_key",
                    atomics=[event],
                    actor_id=account_id,
                    actor_team_id=team_id,
                )
            )
        ],
    )


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
                event_group_id=uuid4(),
                input=Input(),
                team_id=UUID(args.team_id),
                account_id=UUID(args.account_id),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
