from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, Uuid, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from personal_secret.api.core.model import Model

from personal_secret.api.domain.event.event import Event
from personal_secret.api.domain.event.kind import Kind
from personal_secret.api.domain.event.entity_type import EntityType

from personal_secret.api.infrastructure.postgresql.repository import PostgresRepository


# #
# model

class EventModel(Model):
    __tablename__ = "events"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
    )
    kind: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    entity_id: Mapped[UUID] = mapped_column(
        Uuid,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


# #
# mapper

def _to_event(model: EventModel) -> Event:
    event = Event(
        id=model.id,
        kind=Kind.from_str(model.kind),
        entity_type=EntityType.from_str(model.entity_type),
        entity_id=model.entity_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
        by_factory=True,
    )
    return event


# #
# repository

class EventRepository(PostgresRepository[Event, EventModel]):
    model = EventModel
    mapper = _to_event

    # #
    # create

    @classmethod
    async def emit(cls, *, session: AsyncSession, events: list) -> list[Event]:
        return await cls.add_many(
            session=session,
            entities=[
                Event.new(
                    id=event.id(),
                    kind=Kind.from_str(event.kind()),
                    entity_type=EntityType.from_str(event.entity_type()),
                    entity_id=event.entity_id(),
                )
                for event in events
            ],
        )
