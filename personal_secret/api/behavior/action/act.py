from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from personal_secret.api.core.behavior import Action

from personal_secret.api.domain.event.event.event_repository import EventRepository


# #
# act

class Act(Action):

    @staticmethod
    async def claim(session: AsyncSession, *, id: UUID):
        return await EventRepository.claim(session=session, id=id)

    @staticmethod
    async def succeed(session: AsyncSession, *, id: UUID):
        await EventRepository.succeed(session=session, id=id)

    @staticmethod
    async def fail(session: AsyncSession, *, id: UUID, error: str):
        await EventRepository.fail(session=session, id=id, error=error)
