from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from personal_secret.api.core.model import Model

from personal_secret.api.domain.common.exception import NotFoundError

from personal_secret.api.domain.setting.setting import Setting
from personal_secret.api.domain.setting.key import Key
from personal_secret.api.domain.setting.value import Value

from personal_secret.api.infrastructure.postgresql.repository import PostgresRepository


# #
# model

class SettingModel(Model):
    __tablename__ = "settings"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
    )
    key: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    value: Mapped[object] = mapped_column(
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

    __table_args__ = (
        Index(
            "uq_settings_key_active",
            "key",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


# #
# mapper

def _to_setting(model: SettingModel) -> Setting:
    setting = Setting(
        id=model.id,
        key=Key.from_str(model.key),
        value=Value.from_json(model.value),
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
        by_factory=True,
    )
    return setting


# #
# repository

class SettingRepository(PostgresRepository[Setting, SettingModel]):
    model = SettingModel
    mapper = _to_setting

    # #
    # read

    @classmethod
    async def find_by_key(cls, *, session: AsyncSession, key: Key) -> Setting | None:
        return await cls._find_by(session=session, column="key", value=key.to_str())

    @classmethod
    async def get_by_key(cls, *, session: AsyncSession, key: Key) -> Setting:
        setting = await cls.find_by_key(session=session, key=key)
        if setting is None:
            raise NotFoundError("Setting", key.to_str())
        return setting

    @classmethod
    async def list_all(cls, *, session: AsyncSession, limit: int | None = None, offset: int | None = None) -> list[Setting]:
        return await cls._filter(session=session, order_by="key", limit=limit, offset=offset)

    # #
    # command

    @classmethod
    async def set_by_key(cls, *, session: AsyncSession, key: Key, value: Value) -> Setting:
        # upsert — 있으면 value 교체, 없으면 생성
        existing = await cls.find_by_key(session=session, key=key)
        if existing is not None:
            updated = await cls.update(session=session, entity=existing.with_value(value))
            if updated is not None:
                return updated
        return await cls.add(session=session, entity=Setting.new(key=key, value=value))
