from __future__ import annotations

from typing import Any, Callable, Generic, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from personal_secret.api.core.repository import Repository

from personal_secret.api.core.entity import Entity
from personal_secret.api.core.model import Model

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
    async def get_by_id(cls, *, session: AsyncSession, id: UUID) -> E | None:
        return await cls._find(session=session, equals={"id": id})

    @classmethod
    async def get_by_ids(cls, *, session: AsyncSession, ids: list[UUID]) -> list[E]:
        if not ids:
            return []
        return await cls._filter(session=session, in_={"id": ids})

    @classmethod
    async def exists_by_id(cls, *, session: AsyncSession, id: UUID) -> bool:
        return await cls._count(session=session, equals={"id": id}) > 0

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
    async def update_many(cls, *, session: AsyncSession, entities: list[E]) -> list[E]:
        persisted = [await cls.update(session=session, entity=entity) for entity in entities]
        return persisted

    # #
    # delete

    @classmethod
    async def remove_by_id(cls, *, session: AsyncSession, id: UUID) -> E:
        result = await session.execute(
            sql_update(cls.model)
            .where(
                cls.model.id == id,  # type: ignore[attr-defined]
                cls.model.deleted_at.is_(None),  # type: ignore[attr-defined]
            )
            .values(deleted_at=func.now())
            .returning(cls.model)
        )
        model = result.scalars().one()  # 대상 없으면 raise (NoResultFound)
        removed = cls.mapper(model)
        return removed

    # #
    # query — filter + sort + pagination (도메인 finder가 wiring)

    @classmethod
    def _where(
        cls,
        *,
        equals: dict[str, Any] | None = None,
        lte: dict[str, Any] | None = None,
        gte: dict[str, Any] | None = None,
        in_: dict[str, list[Any]] | None = None,
        like: dict[str, str] | None = None,
    ) -> list:
        # soft-delete 제외 + 컬럼별 조건 (전부 AND)
        conditions = [cls.model.deleted_at.is_(None)]  # type: ignore[attr-defined]
        for column, value in (equals or {}).items():
            conditions.append(getattr(cls.model, column) == value)
        for column, value in (lte or {}).items():
            conditions.append(getattr(cls.model, column) <= value)
        for column, value in (gte or {}).items():
            conditions.append(getattr(cls.model, column) >= value)
        for column, values in (in_ or {}).items():
            conditions.append(getattr(cls.model, column).in_(values))
        for column, value in (like or {}).items():
            conditions.append(getattr(cls.model, column).ilike(f"%{value}%"))
        return conditions

    @classmethod
    async def _filter(
        cls,
        *,
        session: AsyncSession,
        equals: dict[str, Any] | None = None,
        lte: dict[str, Any] | None = None,
        gte: dict[str, Any] | None = None,
        in_: dict[str, list[Any]] | None = None,
        like: dict[str, str] | None = None,
        order_by: str | None = None,
        descending: bool = False,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[E]:
        statement = select(cls.model).where(
            *cls._where(equals=equals, lte=lte, gte=gte, in_=in_, like=like)
        )
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
        equals: dict[str, Any] | None = None,
        lte: dict[str, Any] | None = None,
        gte: dict[str, Any] | None = None,
        in_: dict[str, list[Any]] | None = None,
        like: dict[str, str] | None = None,
        order_by: str | None = None,
        descending: bool = False,
    ) -> E | None:
        rows = await cls._filter(
            session=session,
            equals=equals, lte=lte, gte=gte, in_=in_, like=like,
            order_by=order_by, descending=descending, limit=1,
        )
        return rows[0] if rows else None

    @classmethod
    async def _count(
        cls,
        *,
        session: AsyncSession,
        equals: dict[str, Any] | None = None,
        lte: dict[str, Any] | None = None,
        gte: dict[str, Any] | None = None,
        in_: dict[str, list[Any]] | None = None,
        like: dict[str, str] | None = None,
    ) -> int:
        count = await session.scalar(
            select(func.count())
            .select_from(cls.model)
            .where(*cls._where(equals=equals, lte=lte, gte=gte, in_=in_, like=like))
        )
        return count or 0

    @classmethod
    async def _page(
        cls,
        *,
        session: AsyncSession,
        limit: int,
        offset: int = 0,
        equals: dict[str, Any] | None = None,
        lte: dict[str, Any] | None = None,
        gte: dict[str, Any] | None = None,
        in_: dict[str, list[Any]] | None = None,
        like: dict[str, str] | None = None,
        order_by: str | None = None,
        descending: bool = False,
    ) -> tuple[list[E], int]:
        # 한 페이지(items) + 전체 개수(total) — 같은 필터 공유
        items = await cls._filter(
            session=session,
            equals=equals, lte=lte, gte=gte, in_=in_, like=like,
            order_by=order_by, descending=descending, limit=limit, offset=offset,
        )
        total = await cls._count(session=session, equals=equals, lte=lte, gte=gte, in_=in_, like=like)
        return items, total

    # #
    # query sugar (단일 컬럼 — 도메인 finder 가독성)

    @classmethod
    async def _find_by(cls, *, session: AsyncSession, column: str, value: Any) -> E | None:
        return await cls._find(session=session, equals={column: value})

    @classmethod
    async def _exists_by(cls, *, session: AsyncSession, column: str, value: Any) -> bool:
        return await cls._count(session=session, equals={column: value}) > 0

    @classmethod
    async def _filter_by(cls, *, session: AsyncSession, column: str, value: Any) -> list[E]:
        return await cls._filter(session=session, equals={column: value})

    @classmethod
    async def _filter_by_all(cls, *, session: AsyncSession, criteria: dict[str, Any]) -> list[E]:
        return await cls._filter(session=session, equals=criteria)
