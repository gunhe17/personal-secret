from __future__ import annotations

from typing import Any, Callable, Generic, TypeVar
from uuid import UUID

from sqlalchemy import ColumnElement, func, select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from personal_secret.api.core.repository import Repository
from personal_secret.api.core.entity import Entity
from personal_secret.api.core.model import Model

from personal_secret.api.infrastructure.postgresql.exception import UniqueViolationError

E = TypeVar("E", bound=Entity)
M = TypeVar("M", bound=Model)


class PostgresRepository(Repository, Generic[E, M]):
    model: type[M]
    mapper: Callable[[M], E]

    # #
    # create

    @classmethod
    async def add(cls, *, session: AsyncSession, entity: E) -> E:
        model = cls.model(**entity.to_model())  # type: ignore[attr-defined]
        session.add(model)
        await session.flush()
        persisted = cls.mapper(model)
        return persisted

    @classmethod
    async def add_many(cls, *, session: AsyncSession, entities: list[E]) -> list[E]:
        if not entities:
            return []
        models = [cls.model(**e.to_model()) for e in entities]  # type: ignore[attr-defined]
        session.add_all(models)
        await session.flush()
        persisted = [cls.mapper(m) for m in models]
        return persisted

    # #
    # read

    @classmethod
    async def find_by_id(cls, *, session: AsyncSession, id: UUID) -> E | None:
        return await cls._find(session=session, where=[cls.model.id == id])  # type: ignore[attr-defined]

    @classmethod
    async def find_by_ids(cls, *, session: AsyncSession, ids: list[UUID]) -> list[E]:
        if not ids:
            return []
        return await cls._filter(session=session, where=[cls.model.id.in_(ids)])  # type: ignore[attr-defined]

    @classmethod
    async def exists_by_id(cls, *, session: AsyncSession, id: UUID) -> bool:
        return await cls._count(session=session, where=[cls.model.id == id]) > 0  # type: ignore[attr-defined]

    @classmethod
    async def list_all(cls, *, session: AsyncSession) -> list[E]:
        return await cls._filter(session=session)

    # #
    # update

    @classmethod
    async def update(cls, *, session: AsyncSession, entity: E) -> E | None:
        payload = entity.to_model()  # type: ignore[attr-defined]
        id = payload.pop("id")
        result = await session.execute(
            sql_update(cls.model)
            .where(
                cls.model.id == id,  # type: ignore[attr-defined]
                cls.model.deleted_at.is_(None),  # type: ignore[attr-defined]
            )
            .values(**payload, updated_at=func.now())
            .returning(cls.model)
        )
        model = result.scalars().first()
        if model is None:
            return None
        persisted = cls.mapper(model)
        return persisted

    @classmethod
    async def update_many(cls, *, session: AsyncSession, entities: list[E]) -> list[E | None]:
        persisted = [await cls.update(session=session, entity=entity) for entity in entities]
        return persisted

    # #
    # delete

    @classmethod
    async def remove_by_id(cls, *, session: AsyncSession, id: UUID) -> E | None:
        result = await session.execute(
            sql_update(cls.model)
            .where(
                cls.model.id == id,  # type: ignore[attr-defined]
                cls.model.deleted_at.is_(None),  # type: ignore[attr-defined]
            )
            .values(deleted_at=func.now())
            .returning(cls.model)
        )
        model = result.scalars().first()
        if model is None:
            return None
        removed = cls.mapper(model)
        return removed

    # #
    # query

    @classmethod
    async def _filter(
        cls,
        *,
        session: AsyncSession,
        where: list[ColumnElement[bool]] | None = None,
        order_by: str | None = None,
        descending: bool = False,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[E]:
        conditions = [cls.model.deleted_at.is_(None), *(where or [])]  # type: ignore[attr-defined]
        statement = select(cls.model).where(*conditions)
        if order_by is not None:
            column = getattr(cls.model, order_by)
            statement = statement.order_by(column.desc() if descending else column.asc())
        if offset is not None:
            statement = statement.offset(offset)
        if limit is not None:
            statement = statement.limit(limit)
        result = await session.scalars(statement)
        entities = [cls.mapper(m) for m in result]
        return entities

    @classmethod
    async def _find(
        cls,
        *,
        session: AsyncSession,
        where: list[ColumnElement[bool]] | None = None,
        order_by: str | None = None,
        descending: bool = False,
    ) -> E | None:
        rows = await cls._filter(
            session=session,
            where=where,
            order_by=order_by,
            descending=descending,
            limit=1,
        )
        return rows[0] if rows else None

    @classmethod
    async def _count(
        cls,
        *,
        session: AsyncSession,
        where: list[ColumnElement[bool]] | None = None,
    ) -> int:
        conditions = [cls.model.deleted_at.is_(None), *(where or [])]  # type: ignore[attr-defined]
        count = await session.scalar(
            select(func.count())
            .select_from(cls.model)
            .where(*conditions)
        )
        return count or 0

    @classmethod
    async def _page(
        cls,
        *,
        session: AsyncSession,
        limit: int,
        offset: int = 0,
        where: list[ColumnElement[bool]] | None = None,
        order_by: str | None = None,
        descending: bool = False,
    ) -> tuple[list[E], int]:
        items = await cls._filter(
            session=session,
            where=where,
            order_by=order_by,
            descending=descending,
            limit=limit,
            offset=offset,
        )
        total = await cls._count(session=session, where=where)
        return items, total

    # #
    # query sugar

    @classmethod
    async def _find_by(cls, *, session: AsyncSession, column: str, value: Any) -> E | None:
        return await cls._find(session=session, where=[getattr(cls.model, column) == value])

    @classmethod
    async def _exists_by(cls, *, session: AsyncSession, column: str, value: Any) -> bool:
        return await cls._count(session=session, where=[getattr(cls.model, column) == value]) > 0

    @classmethod
    async def _filter_by(cls, *, session: AsyncSession, column: str, value: Any) -> list[E]:
        return await cls._filter(session=session, where=[getattr(cls.model, column) == value])

    @classmethod
    async def _filter_by_all(cls, *, session: AsyncSession, criteria: dict[str, Any]) -> list[E]:
        return await cls._filter(
            session=session,
            where=[getattr(cls.model, column) == value for column, value in criteria.items()],
        )

    # #
    # guard

    @classmethod
    async def _ensure_unique(
        cls,
        *,
        session: AsyncSession,
        entity: E,
        unique: list[str | tuple[str, ...]],
        exclude_id: UUID | None = None,
    ) -> None:
        payload = entity.to_model()  # type: ignore[attr-defined]
        for constraint in unique:
            columns = (constraint,) if isinstance(constraint, str) else tuple(constraint)
            where = [getattr(cls.model, c) == payload[c] for c in columns]
            if exclude_id is not None:
                where.append(cls.model.id != exclude_id)  # type: ignore[attr-defined]
            if await cls._count(session=session, where=where) > 0:
                raise UniqueViolationError(unique_key="+".join(columns))
