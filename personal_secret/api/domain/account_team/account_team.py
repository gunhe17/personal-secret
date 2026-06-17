from __future__ import annotations

from uuid import UUID
from dataclasses import dataclass, replace

from personal_secret.api.core.entity import Entity
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.account_team.role import Role
from personal_secret.api.domain.account_team.team_locked_key import TeamLockedKey


@dataclass(frozen=True, kw_only=True)
class AccountTeam(Entity):
    account_id: UUID
    team_id: UUID
    role: Role
    team_locked_key: TeamLockedKey

    # #
    # factory

    @classmethod
    @typecheck
    def new(
        cls,
        *,
        account_id: UUID,
        team_id: UUID,
        role: Role,
        team_locked_key: TeamLockedKey,
    ) -> "AccountTeam":
        account_team = cls(
            account_id=account_id,
            team_id=team_id,
            role=role,
            team_locked_key=team_locked_key,
            by_factory=True,
        )
        return account_team

    # #
    # update

    def with_team_locked_key(self, team_locked_key: TeamLockedKey) -> "AccountTeam":
        return replace(self, team_locked_key=team_locked_key, by_factory=True)

    # #
    # query

    def to_dict(self):
        return {
            "id": str(self.id),
            "account_id": str(self.account_id),
            "team_id": str(self.team_id),
            "role": self.role.to_str(),
        }

    def to_keys(self):
        return {
            "team_locked_key": self.team_locked_key.to_str(),
        }

    def to_model(self):
        return {
            "id": self.id,
            "account_id": self.account_id,
            "team_id": self.team_id,
            "role": self.role.to_str(),
            "team_locked_key": self.team_locked_key.to_str(),
        }
