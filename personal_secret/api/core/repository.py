from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class Repository(ABC):
    # #
    # create

    @classmethod
    @abstractmethod
    async def add(cls, *, session: AsyncSession, entity: Any) -> Any:
        ...

    @classmethod
    @abstractmethod
    async def add_many(cls, *, session: AsyncSession, entities: list[Any]) -> list[Any]:
        ...

    # #
    # read

    @classmethod
    @abstractmethod
    async def get_by_id(cls, *, session: AsyncSession, id: UUID) -> Any | None:
        ...

    @classmethod
    @abstractmethod
    async def get_by_ids(cls, *, session: AsyncSession, ids: list[UUID]) -> list[Any]:
        ...

    @classmethod
    @abstractmethod
    async def exists_by_id(cls, *, session: AsyncSession, id: UUID) -> bool:
        ...

    @classmethod
    @abstractmethod
    async def list_all(cls, *, session: AsyncSession) -> list[Any]:
        ...

    # #
    # update

    @classmethod
    @abstractmethod
    async def update(cls, *, session: AsyncSession, entity: Any) -> Any:
        ...

    @classmethod
    @abstractmethod
    async def update_many(cls, *, session: AsyncSession, entities: list[Any]) -> list[Any]:
        ...

    # #
    # delete

    @classmethod
    @abstractmethod
    async def remove_by_id(cls, *, session: AsyncSession, id: UUID) -> Any | None:
        ...
