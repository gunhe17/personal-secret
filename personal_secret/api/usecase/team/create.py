from __future__ import annotations

import argparse
import asyncio
from uuid import UUID

from pydantic import BaseModel

from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.team.team import Team
from personal_secret.api.domain.team.team_name import TeamName
from personal_secret.api.domain.team.team_repository import TeamRepository

from personal_secret.api.domain.account_team.account_team import AccountTeam
from personal_secret.api.domain.account_team.role import Role
from personal_secret.api.domain.account_team.team_locked_key import TeamLockedKey
from personal_secret.api.domain.account_team.account_team_repository import AccountTeamRepository

from personal_secret.api.infrastructure.postgresql.client import db_client
from personal_secret.api.infrastructure.postgresql.session import transactional_session


# #
# input

class Input(BaseModel):
    name: str
    # team_locked_key = 클라가 만든 team_key 를 자기 personal_lock 으로 봉인한 것
    team_locked_key: str


# #
# usecase

@typecheck
async def create(*, session, input: Input, account_id: UUID) -> dict:
    # create team (생성자 = 인증된 account)
    team = await TeamRepository.add(
        session=session,
        entity=Team.new(
            name=TeamName.from_str(input.name),
            created_by=account_id,
        ),
    )

    # owner membership
    await AccountTeamRepository.add_unique_by_account_and_team(
        session=session,
        entity=AccountTeam.new(
            account_id=account_id,
            team_id=team.id,
            role=Role.owner(),
            team_locked_key=TeamLockedKey.from_str(input.team_locked_key),
        ),
    )

    # return
    return {"data": team.to_dict()}


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
