from __future__ import annotations

import argparse
import asyncio
from uuid import UUID

from pydantic import BaseModel

from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.account_team.account_team import AccountTeam
from personal_secret.api.domain.account_team.role import Role
from personal_secret.api.domain.account_team.team_locked_key import TeamLockedKey
from personal_secret.api.domain.account_team.account_team_repository import AccountTeamRepository
from personal_secret.api.domain.account_team.account_team_event import AccountTeamEvent

from personal_secret.api.domain.event.event_repository import EventRepository

from personal_secret.api.infrastructure.database.postgresql.client import db_client
from personal_secret.api.infrastructure.database.common.session import transactional_session


# #
# input

class Input(BaseModel):
    account_id: str
    role: str = "member"
    # team_key 를 초대받는이 personal_lock 으로 봉인한 사본 (초대자 클라가 생성)
    team_locked_key: str


# #
# usecase

@typecheck
async def invite(*, session, input: Input, team_id: UUID, actor_id: UUID | None = None) -> dict:
    # persist
    event, membership = AccountTeamEvent.created(
        membership=await AccountTeamRepository.add_unique_by_account_and_team(
            session=session,
            entity=AccountTeam.new(
                account_id=UUID(input.account_id),
                team_id=team_id,
                role=Role.from_str(input.role),
                team_locked_key=TeamLockedKey.from_str(input.team_locked_key),
            ),
        ),
    )

    # return
    return {
        "data": membership.to_dict(),
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
    parser.add_argument("--role", default="member")
    parser.add_argument("--team-locked-key", required=True)
    parser.add_argument("--team-id", required=True)
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await invite(
                session=session,
                input=Input(
                    account_id=args.account_id,
                    role=args.role,
                    team_locked_key=args.team_locked_key,
                ),
                team_id=UUID(args.team_id),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
