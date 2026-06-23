from __future__ import annotations

import argparse
import asyncio
from uuid import UUID, uuid4

from personal_secret.api.core.usecase import In
from personal_secret.api.core.usecase import Out
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.team_access.team_access import TeamAccess
from personal_secret.api.domain.team_access.role import Role
from personal_secret.api.domain.team_access.team_locked_key import TeamLockedKey
from personal_secret.api.domain.team_access.team_access_repository import TeamAccessRepository
from personal_secret.api.domain.team_access.team_access_event import TeamAccessEvent

from personal_secret.api.domain.account.account_repository import AccountRepository
from personal_secret.api.domain.team.team_repository import TeamRepository

from personal_secret.api.domain.event.event.event_repository import EventRepository

from personal_secret.api.infrastructure.database.postgresql.client import db_client
from personal_secret.api.infrastructure.database.common.session import transactional_session


# #
# input

class Input(In):
    account_id: str
    role: str = "member"
    team_locked_key: str


# #
# output

class Output(Out):
    pass


# #
# usecase

@typecheck
async def invite(*, session, event_group_id, input: Input, team_id: UUID, account_id: UUID | None = None) -> Output:
    # context
    invitee = await AccountRepository.get_by_id(
        session=session,
        id=UUID(input.account_id),
    )
    team = await TeamRepository.get_by_id(
        session=session,
        id=team_id,
    )

    # persist
    event, team_access = TeamAccessEvent.created(
        team_access=await TeamAccessRepository.add_unique_by_account_and_team(
            session=session,
            entity=TeamAccess.new(
                account_id=UUID(input.account_id),
                team_id=team_id,
                role=Role.from_str(input.role),
                team_locked_key=TeamLockedKey.from_str(input.team_locked_key),
            ),
        ),
        email=invitee.email.to_str(),
        team_name=team.name.to_str(),
    )

    # return
    return Output(
        data=team_access.to_dict(),
        event=[
            event.to_dict()
            for event in (
                await EventRepository.emit(
                    session=session,
                    id=event_group_id,
                    name="team_invite",
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
                event_group_id=uuid4(),
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
