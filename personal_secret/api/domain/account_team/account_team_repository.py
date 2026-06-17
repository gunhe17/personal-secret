from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String, Uuid, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from personal_secret.api.core.model import Model

from personal_secret.api.domain.common.exception import AlreadyExistsError, NotFoundError

from personal_secret.api.domain.account_team.account_team import AccountTeam
from personal_secret.api.domain.account_team.role import Role
from personal_secret.api.domain.account_team.team_locked_key import TeamLockedKey

from personal_secret.api.infrastructure.database.postgresql.repository import PostgresRepository
from personal_secret.api.infrastructure.database.common.exception import UniqueViolationError


# #
# model

class AccountTeamModel(Model):
    __tablename__ = "account_team"

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
            "uq_account_team_active",
            "account_id",
            "team_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_account_team_team",
            "team_id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


# #
# mapper

def _to_account_team(model: AccountTeamModel) -> AccountTeam:
    account_team = AccountTeam(
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
    return account_team


# #
# repository

class AccountTeamRepository(PostgresRepository[AccountTeam, AccountTeamModel]):
    model = AccountTeamModel
    mapper = _to_account_team

    # #
    # create

    @classmethod
    async def add_unique_by_account_and_team(cls, *, session: AsyncSession, entity: AccountTeam) -> AccountTeam:
        try:
            await cls._ensure_unique(
                session=session,
                entity=entity,
                unique=[("account_id", "team_id")],
            )
        except UniqueViolationError:
            raise AlreadyExistsError("AccountTeam", f"{entity.account_id}/{entity.team_id}")
        return await cls.add(session=session, entity=entity)

    # #
    # read

    @classmethod
    async def find_by_account_and_team(
        cls,
        *,
        session: AsyncSession,
        account_id: UUID,
        team_id: UUID,
    ) -> AccountTeam | None:
        return await cls._find(
            session=session,
            where=[
                AccountTeamModel.account_id == account_id,
                AccountTeamModel.team_id == team_id,
            ],
        )

    @classmethod
    async def get_by_account_and_team(
        cls,
        *,
        session: AsyncSession,
        account_id: UUID,
        team_id: UUID,
    ) -> AccountTeam:
        membership = await cls.find_by_account_and_team(
            session=session,
            account_id=account_id,
            team_id=team_id,
        )
        if membership is None:
            raise NotFoundError("AccountTeam", f"{account_id}/{team_id}")
        return membership

    @classmethod
    async def filter_by_team(cls, *, session: AsyncSession, team_id: UUID) -> list[AccountTeam]:
        return await cls._filter_by(session=session, column="team_id", value=team_id)

    @classmethod
    async def filter_by_account(cls, *, session: AsyncSession, account_id: UUID) -> list[AccountTeam]:
        return await cls._filter_by(session=session, column="account_id", value=account_id)

    # #
    # delete

    @classmethod
    async def remove_by_account_and_team(
        cls,
        *,
        session: AsyncSession,
        account_id: UUID,
        team_id: UUID,
    ) -> AccountTeam:
        membership = await cls.get_by_account_and_team(
            session=session,
            account_id=account_id,
            team_id=team_id,
        )
        return await cls.remove_by_id(session=session, id=membership.id)
