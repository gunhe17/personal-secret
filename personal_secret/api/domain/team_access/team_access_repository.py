from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String, Uuid, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from personal_secret.api.core.model import Model
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.common.exception import AlreadyExistsError, ForbiddenError, NotFoundError

from personal_secret.api.domain.team_access.team_access import TeamAccess
from personal_secret.api.domain.team_access.role import Role
from personal_secret.api.domain.team_access.team_locked_key import TeamLockedKey

from personal_secret.api.infrastructure.database.postgresql.repository import PostgresRepository
from personal_secret.api.infrastructure.database.common.exception import UniqueViolationError


# #
# model

class TeamAccountModel(Model):
    __tablename__ = "team_account"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
    )
    account_id: Mapped[UUID] = mapped_column(
        Uuid,
        nullable=False,
    )
    team_id: Mapped[UUID] = mapped_column(
        Uuid,
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    team_locked_key: Mapped[str] = mapped_column(
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
            "uq_team_account_active",
            "account_id",
            "team_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_team_account_team",
            "team_id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


# #
# mapper

def _to_team_access(model: TeamAccountModel) -> TeamAccess:
    team_access = TeamAccess(
        id=model.id,
        account_id=model.account_id,
        team_id=model.team_id,
        role=Role.from_str(model.role),
        team_locked_key=TeamLockedKey.from_str(model.team_locked_key),
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
        by_factory=True,
    )
    return team_access


# #
# repository

class TeamAccessRepository(PostgresRepository[TeamAccess, TeamAccountModel]):
    model = TeamAccountModel
    mapper = _to_team_access

    # #
    # create

    @classmethod
    @typecheck
    async def add_unique_by_account_and_team(cls, *, session: AsyncSession, entity: TeamAccess) -> TeamAccess:
        try:
            await cls._ensure_unique(
                session=session,
                entity=entity,
                unique=[("account_id", "team_id")],
            )
        except UniqueViolationError:
            raise AlreadyExistsError("TeamAccess", f"{entity.account_id}/{entity.team_id}")
        return await cls.add(session=session, entity=entity)

    # #
    # read

    @classmethod
    @typecheck
    async def find_by_account_and_team(
        cls,
        *,
        session: AsyncSession,
        account_id: UUID,
        team_id: UUID,
    ) -> TeamAccess | None:
        return await cls._find(
            session=session,
            where=[
                TeamAccountModel.account_id == account_id,
                TeamAccountModel.team_id == team_id,
            ],
        )

    @classmethod
    @typecheck
    async def get_by_account_and_team(
        cls,
        *,
        session: AsyncSession,
        account_id: UUID,
        team_id: UUID,
    ) -> TeamAccess:
        team_access = await cls.find_by_account_and_team(
            session=session,
            account_id=account_id,
            team_id=team_id,
        )
        if team_access is None:
            raise NotFoundError("TeamAccess", f"{account_id}/{team_id}")
        return team_access

    @classmethod
    @typecheck
    async def get_valid_by_account_and_team(
        cls,
        *,
        session: AsyncSession,
        account_id: UUID,
        team_id: UUID,
    ) -> TeamAccess:
        team_access = await cls.find_by_account_and_team(
            session=session,
            account_id=account_id,
            team_id=team_id,
        )
        if team_access is None:
            raise ForbiddenError("Team")
        return team_access

    @classmethod
    @typecheck
    async def filter_by_team(cls, *, session: AsyncSession, team_id: UUID) -> list[TeamAccess]:
        return await cls._filter_by(session=session, column="team_id", value=team_id)

    @classmethod
    @typecheck
    async def filter_by_account(cls, *, session: AsyncSession, account_id: UUID) -> list[TeamAccess]:
        return await cls._filter_by(session=session, column="account_id", value=account_id)

    # #
    # delete

    @classmethod
    @typecheck
    async def remove_by_account_and_team(
        cls,
        *,
        session: AsyncSession,
        account_id: UUID,
        team_id: UUID,
    ) -> TeamAccess:
        team_access = await cls.get_by_account_and_team(
            session=session,
            account_id=account_id,
            team_id=team_id,
        )
        removed = await cls.remove_by_id(session=session, id=team_access.id)
        if removed is None:
            raise NotFoundError("TeamAccess", f"{account_id}/{team_id}")
        return removed
