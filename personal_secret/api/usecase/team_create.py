from __future__ import annotations

import argparse
import asyncio
from uuid import UUID

from personal_secret.api.core.usecase import In
from personal_secret.api.core.usecase import Out
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.team.team import Team
from personal_secret.api.domain.team.team_name import TeamName
from personal_secret.api.domain.team.team_repository import TeamRepository
from personal_secret.api.domain.team.team_event import TeamEvent

from personal_secret.api.domain.event.event_repository import EventRepository

from personal_secret.api.domain.account_team.account_team import AccountTeam
from personal_secret.api.domain.account_team.role import Role
from personal_secret.api.domain.account_team.team_locked_key import TeamLockedKey
from personal_secret.api.domain.account_team.account_team_repository import AccountTeamRepository
from personal_secret.api.domain.account_team.account_team_event import AccountTeamEvent

from personal_secret.api.infrastructure.database.postgresql.client import db_client
from personal_secret.api.infrastructure.database.common.session import transactional_session


# #
# input

class Input(In):
    name: str
    # team_locked_key = 클라가 만든 team_key 를 자기 personal_lock 으로 봉인한 것
    team_locked_key: str


# #
# output

class Output(Out):
    pass


# #
# usecase

@typecheck
async def create(*, session, input: Input, account_id: UUID) -> Output:
    # create team
    team_event, team = TeamEvent.created(
        team=await TeamRepository.add(
            session=session,
            entity=Team.new(
                name=TeamName.from_str(input.name),
            ),
        ),
    )

    # owner membership
    member_event, _ = AccountTeamEvent.created(
        membership=await AccountTeamRepository.add_unique_by_account_and_team(
            session=session,
            entity=AccountTeam.new(
                account_id=account_id,
                team_id=team.id,
                role=Role.owner(),
                team_locked_key=TeamLockedKey.from_str(input.team_locked_key),
            ),
        ),
    )

    # return
    return Output.new(
        data=team.to_dict(),
        event=[
            event.to_dict()
            for event in (
                await EventRepository.emit(
                    session=session,
                    events=[team_event, member_event],
                    actor_id=account_id,
                )
            )
        ],
    )


# #
# cli

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--team-locked-key", required=True)
    parser.add_argument("--account-id", required=True)
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await create(
                session=session,
                input=Input(name=args.name, team_locked_key=args.team_locked_key),
                account_id=UUID(args.account_id),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
