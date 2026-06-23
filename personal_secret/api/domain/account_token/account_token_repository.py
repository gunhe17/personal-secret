from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String, Uuid, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from personal_secret.api.core.model import Model
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.common.exception import UnauthorizedError

from personal_secret.api.domain.account_token.account_token import AccountToken
from personal_secret.api.domain.account_token.fingerprint import Fingerprint
from personal_secret.api.domain.account_token.expires_at import ExpiresAt

from personal_secret.api.infrastructure.database.postgresql.repository import PostgresRepository


# #
# model

class AccountTokenModel(Model):
    __tablename__ = "account_tokens"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
    )
    account_id: Mapped[UUID] = mapped_column(
        Uuid,
        nullable=False,
    )
    fingerprint: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
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
            "uq_account_tokens_fingerprint_active",
            "fingerprint",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


# #
# mapper

def _to_account_token(model: AccountTokenModel) -> AccountToken:
    account_token = AccountToken(
        id=model.id,
        account_id=model.account_id,
        fingerprint=Fingerprint.from_str(model.fingerprint),
        expires_at=ExpiresAt.from_datetime(model.expires_at),
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
        by_factory=True,
    )
    return account_token


# #
# repository

class AccountTokenRepository(PostgresRepository[AccountToken, AccountTokenModel]):
    model = AccountTokenModel
    mapper = _to_account_token

    # #
    # read

    @classmethod
    @typecheck
    async def find_by_fingerprint(cls, *, session: AsyncSession, fingerprint: Fingerprint) -> AccountToken | None:
        return await cls._find_by(session=session, column="fingerprint", value=fingerprint.to_str())

    @classmethod
    @typecheck
    async def get_valid_by_fingerprint(cls, *, session: AsyncSession, fingerprint: Fingerprint) -> AccountToken:
        found = await cls._find(
            session=session,
            where=[
                AccountTokenModel.fingerprint == fingerprint.to_str(),
                AccountTokenModel.expires_at > func.now(),
            ],
        )
        if found is None:
            raise UnauthorizedError()
        return found

    # #
    # delete

    @classmethod
    @typecheck
    async def remove_by_fingerprint(cls, *, session: AsyncSession, fingerprint: Fingerprint) -> AccountToken | None:
        account_token = await cls.find_by_fingerprint(session=session, fingerprint=fingerprint)
        if account_token is None:
            return None
        return await cls.remove_by_id(session=session, id=account_token.id)
