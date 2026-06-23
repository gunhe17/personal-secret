from __future__ import annotations

from uuid import UUID
from dataclasses import dataclass
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from personal_secret.api.behavior.action.tenant import Tenant
from personal_secret.api.behavior.action.act import Act

from personal_secret.api.infrastructure.database.postgresql.session import postgresql_transactional_session


# scope
@dataclass(frozen=True)
class Scope:
    # db
    session: AsyncSession
    # actor
    account_id: UUID | None = None
    team_id: UUID | None = None
    # event
    event_group_id: UUID | None = None


# #
# ...

@asynccontextmanager
async def use_postgresql_with_action(
    id: UUID,
    account_id: UUID | None = None,
    team_id: UUID | None = None,
) -> AsyncIterator[Scope | None]:
    # claim
    async with postgresql_transactional_session() as session:
        claimed = await Act.claim(session=session, id=id)
    if claimed is None:
        yield None
        return

    # run
    try:
        async with postgresql_transactional_session() as session:
            if team_id is not None:
                await Tenant.set_tenant_scope(session=session, team_id=team_id)
            yield Scope(
                session=session,
                account_id=account_id,
                team_id=team_id,
                event_group_id=id,
            )
    except Exception as error:
        async with postgresql_transactional_session() as session:
            await Act.fail(session=session, id=id, error=str(error))
        raise

    # succeed
    async with postgresql_transactional_session() as session:
        await Act.succeed(session=session, id=id)