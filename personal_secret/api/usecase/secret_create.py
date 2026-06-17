from __future__ import annotations

import argparse
import asyncio
from uuid import UUID

from pydantic import BaseModel

from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.secret.secret import Secret
from personal_secret.api.domain.secret.domain import Domain
from personal_secret.api.domain.secret.service import Service
from personal_secret.api.domain.secret.project import Project
from personal_secret.api.domain.secret.field import Field
from personal_secret.api.domain.secret.ciphertext import Ciphertext
from personal_secret.api.domain.secret.secret_repository import SecretRepository
from personal_secret.api.domain.secret.secret_event import SecretEvent

from personal_secret.api.domain.event.event_repository import EventRepository

from personal_secret.api.infrastructure.database.postgresql.client import db_client
from personal_secret.api.infrastructure.database.common.session import transactional_session


# #
# input

class Input(BaseModel):
    domain: str
    service: str
    project: str
    field: str
    value: str


# #
# usecase

@typecheck
async def create(*, session, input: Input, team_id: UUID, actor_id: UUID | None = None) -> dict:
    # persist
    event, entity = SecretEvent.created(
        secret=(
            await SecretRepository.add_unique_by_path(
                session=session,
                entity=Secret.new(
                    team_id=team_id,
                    domain=Domain.from_str(input.domain),
                    service=Service.from_str(input.service),
                    project=Project.from_str(input.project),
                    field=Field.from_str(input.field),
                    # value 는 클라가 team_key 로 이미 암호화한 ciphertext(base64)
                    value=Ciphertext.from_str(input.value),
                ),
            )
        )
    )

    # return
    return {
        "data": entity.to_dict(),
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
    parser.add_argument("--domain", required=True)
    parser.add_argument("--service", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--field", required=True)
    parser.add_argument("--value", required=True)
    parser.add_argument("--team-id", required=True)
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await create(
                session=session,
                input=Input(
                    domain=args.domain,
                    service=args.service,
                    project=args.project,
                    field=args.field,
                    value=args.value,
                ),
                team_id=UUID(args.team_id),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
