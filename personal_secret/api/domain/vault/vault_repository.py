from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, Uuid, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from personal_secret.api.core.model import Model

from personal_secret.api.domain.vault.vault import Vault
from personal_secret.api.domain.vault.salt import Salt
from personal_secret.api.domain.vault.wrapped_dek import WrappedDek

from personal_secret.api.infrastructure.postgresql.repository import PostgresRepository


# #
# model

class VaultModel(Model):
    __tablename__ = "vault"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
    )
    salt: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    wrapped_dek: Mapped[str] = mapped_column(
        String,
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

def _to_vault(model: VaultModel) -> Vault:
    vault = Vault(
        id=model.id,
        salt=Salt.from_str(model.salt),
        wrapped_dek=WrappedDek.from_str(model.wrapped_dek),
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
        by_factory=True,
    )
    return vault


# #
# repository

class VaultRepository(PostgresRepository[Vault, VaultModel]):
    model = VaultModel
    mapper = _to_vault

    # #
    # read

    @classmethod
    async def get(cls, *, session: AsyncSession) -> Vault | None:
        # 단일 행 집합체 — 활성 vault는 최대 1개 (init 시 1행 생성)
        vaults = await cls.list_all(session=session)
        return vaults[0] if vaults else None
