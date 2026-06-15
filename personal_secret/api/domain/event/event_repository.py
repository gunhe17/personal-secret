from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, Identity, Index, String, Uuid, func, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from personal_secret.api.core.model import Model

from personal_secret.api.domain.common.exception import NotFoundError

from personal_secret.api.domain.event.event import Event
from personal_secret.api.domain.event.entity_name import EntityName
from personal_secret.api.domain.event.entity_action import EntityAction
from personal_secret.api.domain.event.payload import Payload
from personal_secret.api.domain.event.status import Status
from personal_secret.api.domain.event.succeeded_at import SucceededAt
from personal_secret.api.domain.event.failed_at import FailedAt
from personal_secret.api.domain.event.error import Error

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
    entity_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    entity_action: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    entity_id: Mapped[UUID] = mapped_column(
        Uuid,
        nullable=False,
    )
    team_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        nullable=True,
    )
    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        server_default=text("'pending'"),
    )
    succeeded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
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

    __table_args__ = (
        Index(
            "ix_events_pending",
            "sequence",
            postgresql_where=text("status = 'pending' AND deleted_at IS NULL"),
        ),
    )


# #
# mapper

def _to_event(model: EventModel) -> Event:
    event = Event(
        id=model.id,
        sequence=model.sequence,
        entity_name=EntityName.from_str(model.entity_name),
        entity_action=EntityAction.from_str(model.entity_action),
        entity_id=model.entity_id,
        team_id=model.team_id,
        payload=Payload.from_dict(model.payload),
        status=Status.from_str(model.status),
        succeeded_at=(
            SucceededAt.from_datetime(model.succeeded_at) if model.succeeded_at else None
        ),
        failed_at=(
            FailedAt.from_datetime(model.failed_at) if model.failed_at else None
        ),
        error=(
            Error.from_str(model.error) if model.error else None
        ),
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
                    entity_name=EntityName.from_str(event.entity_name()),
                    entity_action=EntityAction.from_str(event.entity_action()),
                    entity_id=event.entity_id(),
                    payload=Payload.from_dict(event.payload()),
                    team_id=event.team_id(),
                )
                for event in events
            ],
        )

    # #
    # consume (outbox)

    @classmethod
    async def claim_pending(cls, *, session: AsyncSession, limit: int) -> list[Event]:
        # FOR UPDATE SKIP LOCKED — 코어 _filter 에 없는 잠금이라 직접 구성
        statement = (
            select(EventModel)
            .where(
                EventModel.deleted_at.is_(None),
                EventModel.status == "pending",
            )
            .order_by(EventModel.sequence.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        rows = await session.scalars(statement)
        return [
            cls.mapper(model) for model in rows
        ]

    @classmethod
    async def succeed(cls, *, session: AsyncSession, event: Event) -> Event:
        succeeded = event.succeed(
            at=SucceededAt.from_datetime(datetime.now(timezone.utc)),
        )
        return await cls._persist(session=session, entity=succeeded)

    @classmethod
    async def fail(cls, *, session: AsyncSession, event: Event, error: str) -> Event:
        failed = event.fail(
            at=FailedAt.from_datetime(datetime.now(timezone.utc)),
            error=Error.from_str(error),
        )
        return await cls._persist(session=session, entity=failed)

    # #
    # internal

    @classmethod
    async def _persist(cls, *, session: AsyncSession, entity: Event) -> Event:
        updated = await super().update(session=session, entity=entity)
        if updated is None:
            raise NotFoundError("Event", str(entity.id))
        return updated
