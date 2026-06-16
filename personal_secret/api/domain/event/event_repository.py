from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, Identity, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from personal_secret.api.core.model import Model

from personal_secret.api.domain.event.event import Event
from personal_secret.api.domain.event.act import Act
from personal_secret.api.domain.event.entity_name import EntityName
from personal_secret.api.domain.event.payload import Payload

from personal_secret.api.infrastructure.postgresql.repository import PostgresRepository


# #
# model

class EventModel(Model):
    __tablename__ = "events"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
    )
    sequence: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        nullable=False,
        unique=True,
    )
    act_group_id: Mapped[UUID] = mapped_column(
        Uuid,
        nullable=False,
    )
    actor_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        nullable=True,
    )
    actor_team_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        nullable=True,
    )
    act: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    act_entity_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    act_entity_id: Mapped[UUID] = mapped_column(
        Uuid,
        nullable=False,
    )
    payload: Mapped[dict] = mapped_column(
        JSONB,
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
        sequence=model.sequence,
        act_group_id=model.act_group_id,
        actor_id=model.actor_id,
        actor_team_id=model.actor_team_id,
        act=Act.from_str(model.act),
        act_entity_name=EntityName.from_str(model.act_entity_name),
        act_entity_id=model.act_entity_id,
        payload=Payload.from_dict(model.payload),
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
    async def emit(
        cls,
        *,
        session: AsyncSession,
        events: list,
        actor_id: UUID | None = None,
        actor_team_id: UUID | None = None,
    ) -> list[Event]:
        # act_group_id — 한 emit(=한 액션)의 이벤트들을 묶는 키
        act_group_id = uuid4()
        return await cls.add_many(
            session=session,
            entities=[
                Event.new(
                    id=event.id(),
                    act=Act.from_str(event.act()),
                    act_entity_name=EntityName.from_str(event.act_entity_name()),
                    act_entity_id=event.act_entity_id(),
                    payload=Payload.from_dict(event.payload()),
                    act_group_id=act_group_id,
                    actor_id=actor_id,
                    actor_team_id=actor_team_id,
                )
                for event in events
            ],
        )
