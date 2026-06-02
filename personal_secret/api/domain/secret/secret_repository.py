from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from personal_secret.api.core.model import Model

from personal_secret.api.domain.secret.secret import Secret
from personal_secret.api.domain.secret.kind import Kind
from personal_secret.api.domain.secret.name import Name
from personal_secret.api.domain.secret.tags import Tags
from personal_secret.api.domain.secret.expires_at import ExpiresAt
from personal_secret.api.domain.secret.ciphertext import Ciphertext

from personal_secret.api.infrastructure.postgresql.repository import PostgresRepository


# #
# model

class SecretModel(Model):
    __tablename__ = "secrets"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
    )
    kind: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    tags: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
    )
    ciphertext: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
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

    __table_args__ = (
        Index(
            "uq_secrets_name_active",
            "name",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


# #
# mapper

def _to_secret(model: SecretModel) -> Secret:
    secret = Secret(
        id=model.id,
        kind=Kind.from_str(model.kind),
        name=Name.from_str(model.name),
        tags=Tags.from_list(model.tags),
        ciphertext=Ciphertext.from_str(model.ciphertext),
        expires_at=ExpiresAt.from_datetime(model.expires_at) if model.expires_at else None,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
        by_factory=True,
    )
    return secret


# #
# repository

class SecretRepository(PostgresRepository[Secret, SecretModel]):
    model = SecretModel
    mapper = _to_secret

    # #
    # read

    @classmethod
    async def find_by_name(cls, *, session: AsyncSession, name: Name) -> Secret | None:
        secret = await cls._find_by(session=session, column="name", value=name.to_str())
        return secret

    @classmethod
    async def exists_by_name(cls, *, session: AsyncSession, name: Name) -> bool:
        return await cls._exists_by(session=session, column="name", value=name.to_str())

    @classmethod
    async def find_by_identifier(cls, *, session: AsyncSession, identifier: str) -> Secret | None:
        try:
            id = UUID(identifier)
        except ValueError:
            secret = await cls.find_by_name(session=session, name=Name.from_str(identifier))
            return secret
        secret = await cls.get_by_id(session=session, id=id)
        return secret

    @classmethod
    async def filter_by_kind(cls, *, session: AsyncSession, kind: Kind) -> list[Secret]:
        secrets = await cls._filter_by(session=session, column="kind", value=kind.to_str())
        return secrets

    @classmethod
    async def filter_expiring_between(cls, *, session: AsyncSession, start: datetime, end: datetime) -> list[Secret]:
        # start ≤ expires_at ≤ end (이미 만료된 건 start 하한으로 제외), soonest first
        secrets = await cls._filter(
            session=session,
            gte={"expires_at": start},
            lte={"expires_at": end},
            order_by="expires_at",
        )
        return secrets
