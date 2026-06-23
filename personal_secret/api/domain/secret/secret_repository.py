from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String, Uuid, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from personal_secret.api.core.model import Model
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.common.exception import AlreadyExistsError, NotFoundError

from personal_secret.api.domain.secret.secret import Secret
from personal_secret.api.domain.secret.domain import Domain
from personal_secret.api.domain.secret.service import Service
from personal_secret.api.domain.secret.project import Project
from personal_secret.api.domain.secret.field import Field
from personal_secret.api.domain.secret.ciphertext import Ciphertext

from personal_secret.api.infrastructure.database.postgresql.repository import PostgresRepository
from personal_secret.api.infrastructure.database.common.exception import UniqueViolationError


# #
# model

class SecretModel(Model):
    __tablename__ = "secrets"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
    )
    team_id: Mapped[UUID] = mapped_column(
        Uuid,
        nullable=False,
    )
    domain: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    service: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    project: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    field: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    value: Mapped[str] = mapped_column(
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
            "uq_secrets_path_active",
            "team_id",
            "domain",
            "service",
            "project",
            "field",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_secrets_scope",
            "team_id",
            "domain",
            "service",
            "project",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


# #
# mapper

def _to_secret(model: SecretModel) -> Secret:
    secret = Secret(
        id=model.id,
        team_id=model.team_id,
        domain=Domain.from_str(model.domain),
        service=Service.from_str(model.service),
        project=Project.from_str(model.project),
        field=Field.from_str(model.field),
        value=Ciphertext.from_str(model.value),
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
        by_factory=True,
    )
    return secret


# #
# repository

# 모든 finder 는 team_id 로 스코프한다. 테넌트 격리의 DB 백스톱은 RLS
class SecretRepository(PostgresRepository[Secret, SecretModel]):
    model = SecretModel
    mapper = _to_secret

    # #
    # create

    @classmethod
    @typecheck
    async def add_unique_by_path(cls, *, session: AsyncSession, entity: Secret) -> Secret:
        try:
            await cls._ensure_unique(
                session=session,
                entity=entity,
                unique=[("team_id", "domain", "service", "project", "field")],
            )
        except UniqueViolationError:
            raise AlreadyExistsError("Secret", _path(entity))
        return await cls.add(session=session, entity=entity)

    # #
    # read

    @classmethod
    @typecheck
    async def get_by_id(cls, *, session: AsyncSession, id: UUID, team_id: UUID) -> Secret:
        # 다른 팀 secret 은 존재해도 NotFound (존재 노출 방지)
        secret = await cls._find(
            session=session,
            where=[SecretModel.id == id, SecretModel.team_id == team_id],
        )
        if secret is None:
            raise NotFoundError("Secret", str(id))
        return secret

    @classmethod
    @typecheck
    async def find_by_path(
        cls,
        *,
        session: AsyncSession,
        team_id: UUID,
        domain: Domain,
        service: Service,
        project: Project,
        field: Field,
    ) -> Secret | None:
        return await cls._find(
            session=session,
            where=[
                SecretModel.team_id == team_id,
                SecretModel.domain == domain.to_str(),
                SecretModel.service == service.to_str(),
                SecretModel.project == project.to_str(),
                SecretModel.field == field.to_str(),
            ],
        )

    @classmethod
    @typecheck
    async def search(
        cls,
        *,
        session: AsyncSession,
        team_id: UUID,
        domain: Domain | None = None,
        service: Service | None = None,
        project: Project | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Secret]:
        where = [SecretModel.team_id == team_id]
        if domain is not None:
            where.append(SecretModel.domain == domain.to_str())
        if service is not None:
            where.append(SecretModel.service == service.to_str())
        if project is not None:
            where.append(SecretModel.project == project.to_str())
        return await cls._filter(
            session=session,
            where=where,
            order_by="field",
            limit=limit,
            offset=offset,
        )

    # #
    # update

    @classmethod
    @typecheck
    async def update(cls, *, session: AsyncSession, entity: Secret) -> Secret:
        updated = await super().update(session=session, entity=entity)
        if updated is None:
            raise NotFoundError("Secret", str(entity.id))
        return updated

    # #
    # delete

    @classmethod
    @typecheck
    async def remove_by_id(cls, *, session: AsyncSession, id: UUID) -> Secret:
        removed = await super().remove_by_id(session=session, id=id)
        if removed is None:
            raise NotFoundError("Secret", str(id))
        return removed


# #
# internal

def _path(secret: Secret) -> str:
    return "/".join(
        [
            secret.domain.to_str(),
            secret.service.to_str(),
            secret.project.to_str(),
            secret.field.to_str(),
        ]
    )
