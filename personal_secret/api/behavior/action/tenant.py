from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from personal_secret.api.core.behavior import Action
from personal_secret.api.infrastructure.database.postgresql.rls import TENANT_SETTING


# #
# action

class Tenant(Action):
    
    @staticmethod
    async def set_tenant_scope(
        session: AsyncSession, 
        *, 
        team_id: UUID
    ):
        await session.execute(
            text(f"SELECT set_config('{TENANT_SETTING}', :team, true)"),
            {"team": str(team_id)},
        )