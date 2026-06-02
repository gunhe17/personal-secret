from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel

from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.secret.secret_repository import SecretRepository

from personal_secret.api.infrastructure.postgresql.client import db_client
from personal_secret.api.infrastructure.postgresql.session import transactional_session


# #
# input

class Input(BaseModel):
    within_days: int = 30


# #
# usecase

@typecheck
async def list_expiring(*, session, input: Input) -> list[dict]:
    # window — now ~ now+N일 사이 만료분만 (이미 만료된 건 제외), 정렬은 repo가 책임
    now = datetime.now(timezone.utc)
    secrets = await SecretRepository.filter_expiring_between(
        session=session,
        start=now,
        end=now + timedelta(days=input.within_days),
    )

    expiring = [s.to_dict() for s in secrets]
    
    return expiring


# #
# cli

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--within-days", type=int, default=30)
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(await list_expiring(
            session=session,
            input=Input(within_days=args.within_days),
        ))

if __name__ == "__main__":
    asyncio.run(_main())
