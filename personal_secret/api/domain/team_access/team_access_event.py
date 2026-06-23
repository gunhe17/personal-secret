from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from personal_secret.api.core.event import Event
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.team_access.team_access import TeamAccess


class TeamAccessEventKind(Enum):
    CREATED = "created"
    DELETED = "deleted"
    READ = "read"


@dataclass(frozen=True, kw_only=True)
class TeamAccessEvent(Event):
    _kind: TeamAccessEventKind
    team_access: TeamAccess
    _email: str | None = None
    _team_name: str | None = None

    # #
    # factory

    @classmethod
    @typecheck
    def created(
        cls,
        *,
        team_access: TeamAccess,
        email: str | None = None,
        team_name: str | None = None,
    ) -> tuple["TeamAccessEvent", TeamAccess]:
        return cls(_kind=TeamAccessEventKind.CREATED, team_access=team_access, _email=email, _team_name=team_name), team_access

    @classmethod
    @typecheck
    def deleted(
        cls,
        *,
        team_access: TeamAccess,
        email: str | None = None,
        team_name: str | None = None,
    ) -> tuple["TeamAccessEvent", TeamAccess]:
        return cls(_kind=TeamAccessEventKind.DELETED, team_access=team_access, _email=email, _team_name=team_name), team_access

    @classmethod
    @typecheck
    def read(cls, *, team_access: TeamAccess) -> tuple["TeamAccessEvent", TeamAccess]:
        return cls(_kind=TeamAccessEventKind.READ, team_access=team_access), team_access

    # #
    # query

    def act(self) -> str:
        return self._kind.value

    def act_entity_name(self) -> str:
        return "team_access"

    def act_entity_id(self) -> UUID:
        return self.team_access.id

    def payload(self) -> dict:
        payload = {
            "account_id": str(self.team_access.account_id),
            "role": self.team_access.role.to_str(),
        }
        if self._email is not None:
            payload["email"] = self._email
        if self._team_name is not None:
            payload["team_name"] = self._team_name
        return payload
