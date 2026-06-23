from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import DateTime, Integer, String, Uuid, func, select
from sqlalchemy import update as sql_update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from personal_secret.api.core.model import Model
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.event.event.event import Event
from personal_secret.api.domain.event.event.event_name import EventName
from personal_secret.api.domain.event.event.dispatch_status import DispatchStatus
from personal_secret.api.domain.event.event.attempts import Attempts
from personal_secret.api.domain.event.event.errors import Errors

from personal_secret.api.domain.event.atomic_event.atomic_event import AtomicEvent
from personal_secret.api.domain.event.atomic_event.atomic_event_model import AtomicEventModel
from personal_secret.api.domain.event.atomic_event.atomic_event_model import _to_atomic_event

from personal_secret.api.infrastructure.database.postgresql.repository import PostgresRepository


# #
# model

class EventModel(Model):
    __tablename__ = "events"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    errors: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
    )
    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    succeeded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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


# #
# mapper

def _to_event(model: EventModel) -> Event:
    event = Event(
        id=model.id,
        name=EventName.from_str(model.name),
        status=DispatchStatus.from_str(model.status),
        attempts=Attempts.from_int(model.attempts),
        errors=Errors.from_list(model.errors),
        claimed_at=model.claimed_at,
        succeeded_at=model.succeeded_at,
        failed_at=model.failed_at,
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
    @typecheck
    async def emit(
        cls,
        *,
        session: AsyncSession,
        id: UUID,
        name: str,
        atomics: list,
        actor_id: UUID | None = None,
        actor_team_id: UUID | None = None,
    ) -> list[AtomicEvent]:
        # event
        statement = (
            pg_insert(cls.model)
            .values(**Event.new(id=id, name=EventName.from_str(name)).to_model())
            .on_conflict_do_nothing(index_elements=["id"])
        )
        await session.execute(statement)

        # atomic
        entities = [
            AtomicEvent.from_marker(
                marker=marker,
                event_id=id,
                actor_id=actor_id,
                actor_team_id=actor_team_id,
            )
            for marker in atomics
        ]
        models = [AtomicEventModel(**entity.to_model()) for entity in entities]
        session.add_all(models)
        await session.flush()
        return [
            _to_atomic_event(model) for model in models
        ]

    # #
    # claim

    @classmethod
    @typecheck
    async def claim(cls, *, session: AsyncSession, id: UUID) -> Event | None:
        result = await session.execute(
            sql_update(cls.model)
            .where(
                cls.model.id == id,
                cls.model.status == DispatchStatus.pending().to_str(),
            )
            .values(
                status=DispatchStatus.claimed().to_str(),
                claimed_at=func.now(),
                updated_at=func.now(),
            )
            .returning(cls.model)
        )
        model = result.scalar_one_or_none()
        return cls.mapper(model) if model else None

    # #
    # transition

    @classmethod
    @typecheck
    async def succeed(cls, *, session: AsyncSession, id: UUID) -> Event | None:
        found = await cls.find_by_id(session=session, id=id)
        if found is None:
            return None
        return await cls.update(
            session=session,
            entity=found.succeed(at=datetime.now(timezone.utc)),
        )

    @classmethod
    @typecheck
    async def fail(cls, *, session: AsyncSession, id: UUID, error: str, max_attempts: int = 5) -> Event | None:
        found = await cls.find_by_id(session=session, id=id)
        if found is None:
            return None
        return await cls.update(
            session=session,
            entity=found.fail(at=datetime.now(timezone.utc), error=error, max_attempts=max_attempts),
        )

    # #
    # atomic

    @classmethod
    @typecheck
    async def filter_by_event_id(cls, *, session: AsyncSession, event_id: UUID) -> list[AtomicEvent]:
        result = await session.scalars(
            select(AtomicEventModel)
            .where(
                AtomicEventModel.event_id == event_id,
                AtomicEventModel.deleted_at.is_(None),
            )
            .order_by(AtomicEventModel.sequence.asc())
        )
        return [
            _to_atomic_event(model) for model in result
        ]
