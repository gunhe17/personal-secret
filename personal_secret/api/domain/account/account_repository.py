from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String, Uuid, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from personal_secret.api.core.model import Model
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.common.exception import AlreadyExistsError, InvalidCredentialError, NotFoundError

from personal_secret.api.domain.account.account import Account
from personal_secret.api.domain.account.email import Email
from personal_secret.api.domain.account.personal_lock import PersonalLock
from personal_secret.api.domain.account.personal_locked_key import PersonalLockedKey
from personal_secret.api.domain.account.personal_unlock_salt import PersonalUnlockSalt
from personal_secret.api.domain.account.login_salt import LoginSalt
from personal_secret.api.domain.account.login_verifier import LoginVerifier

from personal_secret.api.infrastructure.database.postgresql.repository import PostgresRepository
from personal_secret.api.infrastructure.database.common.exception import UniqueViolationError


# #
# model

class AccountModel(Model):
    __tablename__ = "accounts"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
    )
    email: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    personal_lock: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    personal_locked_key: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    personal_unlock_salt: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    login_salt: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    login_verifier: Mapped[str] = mapped_column(
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

    __table_args__ = (
        Index(
            "uq_accounts_email_active",
            "email",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


# #
# mapper

def _to_account(model: AccountModel) -> Account:
    account = Account(
        id=model.id,
        email=Email.from_str(model.email),
        personal_lock=PersonalLock.from_str(model.personal_lock),
        personal_locked_key=PersonalLockedKey.from_str(model.personal_locked_key),
        personal_unlock_salt=PersonalUnlockSalt.from_str(model.personal_unlock_salt),
        login_salt=LoginSalt.from_str(model.login_salt),
        login_verifier=LoginVerifier.from_str(model.login_verifier),
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
        by_factory=True,
    )
    return account


# #
# repository

class AccountRepository(PostgresRepository[Account, AccountModel]):
    model = AccountModel
    mapper = _to_account

    # #
    # create

    @classmethod
    @typecheck
    async def add_unique_by_email(cls, *, session: AsyncSession, entity: Account) -> Account:
        try:
            await cls._ensure_unique(session=session, entity=entity, unique=["email"])
        except UniqueViolationError:
            raise AlreadyExistsError("Account", entity.email.to_str())
        return await cls.add(session=session, entity=entity)

    # #
    # read

    @classmethod
    @typecheck
    async def find_by_email(cls, *, session: AsyncSession, email: Email) -> Account | None:
        return await cls._find_by(session=session, column="email", value=email.to_str())

    @classmethod
    @typecheck
    async def get_by_email(cls, *, session: AsyncSession, email: Email) -> Account:
        account = await cls.find_by_email(session=session, email=email)
        if account is None:
            raise NotFoundError("Account", email.to_str())
        return account

    @classmethod
    @typecheck
    async def get_by_id(cls, *, session: AsyncSession, id: UUID) -> Account:
        account = await cls.find_by_id(session=session, id=id)
        if account is None:
            raise NotFoundError("Account", str(id))
        return account

    @classmethod
    @typecheck
    async def verify_email(cls, *, session: AsyncSession, email: Email) -> Account:
        # 부재 = InvalidCredentialError (NotFound 아님) — 로그인이 이메일 존재 여부 노출 안 하게
        account = await cls.find_by_email(session=session, email=email)
        if account is None:
            raise InvalidCredentialError()
        return account