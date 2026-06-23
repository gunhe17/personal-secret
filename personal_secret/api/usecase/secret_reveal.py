from __future__ import annotations

import argparse
import asyncio
from uuid import UUID, uuid4

from personal_secret.api.core.usecase import In
from personal_secret.api.core.usecase import Out
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.secret.secret_repository import SecretRepository
from personal_secret.api.domain.secret.secret_event import SecretEvent

from personal_secret.api.domain.event.event.event_repository import EventRepository

from personal_secret.api.infrastructure.database.postgresql.client import db_client
from personal_secret.api.infrastructure.database.common.session import transactional_session


# #
# input

class Input(In):
    id: str


# #
# output

class Output(Out):
    pass


# #
# usecase

@typecheck
async def reveal(*, session, event_group_id, input: Input, team_id: UUID, account_id: UUID | None = None) -> Output:
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

    # return
    return Output(
        data={
            **secret.to_dict(),
            "value": secret.value.to_str(),
        },
        event=[
            event.to_dict()
            for event in (
                await EventRepository.emit(
                    session=session,
                    id=event_group_id,
                    name="secret_reveal",
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
    parser.add_argument("id")
    parser.add_argument("--team-id", required=True)
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await reveal(
                session=session,
                event_group_id=uuid4(),
                input=Input(id=args.id),
                team_id=UUID(args.team_id),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
