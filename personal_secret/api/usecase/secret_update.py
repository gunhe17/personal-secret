from __future__ import annotations

import argparse
import asyncio
from uuid import UUID

from personal_secret.api.core.usecase import In
from personal_secret.api.core.usecase import Out
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.secret.ciphertext import Ciphertext
from personal_secret.api.domain.secret.secret_repository import SecretRepository
from personal_secret.api.domain.secret.secret_event import SecretEvent

from personal_secret.api.domain.event.event_repository import EventRepository

from personal_secret.api.infrastructure.database.postgresql.client import db_client
from personal_secret.api.infrastructure.database.common.session import transactional_session


# #
# input

class Input(In):
    id: str
    value: str


# #
# output

class Output(Out):
    pass


# #
# usecase

@typecheck
async def update(*, session, input: Input, team_id: UUID, actor_id: UUID | None = None) -> Output:
    # find
    found = await SecretRepository.get_by_id(
        session=session,
        id=UUID(input.id),
        team_id=team_id,
    )

    # update (value 는 클라가 team_key 로 암호화한 ciphertext)
    updated = found.with_value(Ciphertext.from_str(input.value))

    # persist
    event, secret = SecretEvent.updated(
        secret=(
            await SecretRepository.update(
                session=session,
                entity=updated,
            )
        )
    )

    # return
    return Output.new(
        data=secret.to_dict(),
        event=[
            e.to_dict()
            for e in (
                await EventRepository.emit(
                    session=session,
                    events=[event],
                    actor_id=actor_id,
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
    parser.add_argument("--value", required=True)
    parser.add_argument("--team-id", required=True)
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await update(
                session=session,
                input=Input(id=args.id, value=args.value),
                team_id=UUID(args.team_id),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
