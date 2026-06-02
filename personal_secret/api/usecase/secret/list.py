from __future__ import annotations

import argparse
import asyncio

from pydantic import BaseModel

from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.secret.kind import Kind
from personal_secret.api.domain.secret.secret_repository import SecretRepository

from personal_secret.api.infrastructure.postgresql.client import db_client
from personal_secret.api.infrastructure.postgresql.session import transactional_session


# #
# input

class Input(BaseModel):
    kind: str | None = None
    tag: str | None = None
    query: str | None = None


# #
# usecase

@typecheck
async def list_secrets(*, session, input: Input) -> list[dict]:
    # fetch
    if input.kind is not None:
        secrets = await SecretRepository.filter_by_kind(session=session, kind=Kind.from_str(input.kind))
    else:
        secrets = await SecretRepository.list_all(session=session)

    # filter
    if input.tag is not None:
        secrets = [s for s in secrets if input.tag in s.tags.to_list()]
    if input.query is not None:
        needle = input.query.lower()
        secrets = [s for s in secrets if needle in s.name.to_str().lower()]

    # sort
    secrets = sorted(secrets, key=lambda s: s.name.to_str())

    listed = [s.to_dict() for s in secrets]
    return listed


# #
# cli

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", default=None)
    parser.add_argument("--tag", default=None)
    parser.add_argument("--query", default=None)
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(await list_secrets(
            session=session,
            input=Input(kind=args.kind, tag=args.tag, query=args.query),
        ))

if __name__ == "__main__":
    asyncio.run(_main())
