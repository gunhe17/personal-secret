from __future__ import annotations

import argparse
import asyncio
from uuid import UUID

from pydantic import BaseModel

from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.secret.domain import Domain
from personal_secret.api.domain.secret.service import Service
from personal_secret.api.domain.secret.project import Project
from personal_secret.api.domain.secret.secret_repository import SecretRepository
from personal_secret.api.domain.secret.secret_event import SecretEvent

from personal_secret.api.domain.event.event_repository import EventRepository

from personal_secret.api.infrastructure.postgresql.client import db_client
from personal_secret.api.infrastructure.postgresql.session import transactional_session


# #
# input

class Input(BaseModel):
    domain: str | None = None
    service: str | None = None
    project: str | None = None
    limit: int | None = None
    offset: int | None = None


# #
# usecase

@typecheck
async def list_secrets(*, session, input: Input, team_id: UUID, actor_id: UUID | None = None) -> dict:
    # find
    founds = SecretEvent.read_many(
        secrets=(
            await SecretRepository.search(
                session=session,
                team_id=team_id,
                domain=(
                    Domain.from_str(input.domain) if input.domain is not None else None
                ),
                service=(
                    Service.from_str(input.service) if input.service is not None else None
                ),
                project=(
                    Project.from_str(input.project) if input.project is not None else None
                ),
                limit=input.limit,
                offset=input.offset,
            )
        )
    )

    # emit
    await EventRepository.emit(
        session=session,
        events=[event for event, _ in founds],
        actor_id=actor_id,
        actor_team_id=team_id,
    )

    # return
    return {
        "data": [secret.to_dict() for _, secret in founds],
    }


# #
# cli

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", default=None)
    parser.add_argument("--service", default=None)
    parser.add_argument("--project", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--offset", type=int, default=None)
    parser.add_argument("--team-id", required=True)
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await list_secrets(
                session=session,
                input=Input(
                    domain=args.domain,
                    service=args.service,
                    project=args.project,
                    limit=args.limit,
                    offset=args.offset,
                ),
                team_id=UUID(args.team_id),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
