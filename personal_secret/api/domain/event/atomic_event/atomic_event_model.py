from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, Identity, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from personal_secret.api.core.model import Model

from personal_secret.api.domain.event.atomic_event.atomic_event import AtomicEvent
from personal_secret.api.domain.event.atomic_event.act import Act
from personal_secret.api.domain.event.atomic_event.entity_name import EntityName
from personal_secret.api.domain.event.atomic_event.payload import Payload


# #
# model

class AtomicEventModel(Model):
    __tablename__ = "atomic_events"

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
    event_id: Mapped[UUID] = mapped_column(
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

def _to_atomic_event(model: AtomicEventModel) -> AtomicEvent:
    atomic_event = AtomicEvent(
        id=model.id,
        sequence=model.sequence,
        event_id=model.event_id,
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
    return atomic_event


# repository 는 aggregate root EventRepository 에 있다
