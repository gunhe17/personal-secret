from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from personal_secret.api.core.model import Model

from personal_secret.api.domain.team.team import Team
from personal_secret.api.domain.team.team_name import TeamName

from personal_secret.api.infrastructure.database.postgresql.repository import PostgresRepository


# #
# model

class TeamModel(Model):
    __tablename__ = "teams"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(
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

def _to_team(model: TeamModel) -> Team:
    team = Team(
        id=model.id,
        name=TeamName.from_str(model.name),
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
        by_factory=True,
    )
    return team


# #
# repository

class TeamRepository(PostgresRepository[Team, TeamModel]):
    model = TeamModel
    mapper = _to_team
