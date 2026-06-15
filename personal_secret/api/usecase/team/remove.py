from __future__ import annotations

import argparse
import asyncio
from uuid import UUID

from pydantic import BaseModel

from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.common.exception import NotFoundError

from personal_secret.api.domain.account_team.account_team_repository import AccountTeamRepository

from personal_secret.api.infrastructure.postgresql.client import db_client
from personal_secret.api.infrastructure.postgresql.session import transactional_session


# #
# input

class Input(BaseModel):
    account_id: str


# #
# usecase

@typecheck
async def remove(*, session, input: Input, team_id: UUID) -> dict:
    # 멤버십 삭제 → team_key 경로 차단 (전방안전성은 rotate 로 별도)
    removed = await AccountTeamRepository.remove_by_account_and_team(
        session=session,
        account_id=UUID(input.account_id),
        team_id=team_id,
    )
    if removed is None:
        raise NotFoundError("AccountTeam", input.account_id)

    # return
    return {"data": removed.to_dict()}


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
