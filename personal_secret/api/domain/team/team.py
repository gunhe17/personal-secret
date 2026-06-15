from __future__ import annotations

from uuid import UUID
from dataclasses import dataclass

from personal_secret.api.core.entity import Entity
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.team.team_name import TeamName


@dataclass(frozen=True, kw_only=True)
class Team(Entity):
    name: TeamName
    created_by: UUID

    # #
    # factory

    @classmethod
    @typecheck
    def new(cls, *, name: TeamName, created_by: UUID) -> "Team":
        team = cls(
            name=name,
            created_by=created_by,
            by_factory=True,
        )
        return team

    # #
    # query

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name.to_str(),
            "created_by": str(self.created_by),
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }

    def to_model(self):
        return {
            "id": self.id,
            "name": self.name.to_str(),
            "created_by": self.created_by,
        }
