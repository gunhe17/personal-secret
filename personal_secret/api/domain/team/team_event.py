from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from personal_secret.api.core.event import Event
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.team.team import Team


class TeamEventKind(Enum):
    CREATED = "created"
    ROTATED = "rotated"


@dataclass(frozen=True, kw_only=True)
class TeamEvent(Event):
    _kind: TeamEventKind
    _act_entity_id: UUID
    _name: str | None = None

    # #
    # factory

    @classmethod
    @typecheck
    def created(cls, *, team: Team) -> tuple["TeamEvent", Team]:
        return cls(_kind=TeamEventKind.CREATED, _act_entity_id=team.id, _name=team.name.to_str()), team

    @classmethod
    @typecheck
    def rotated(cls, *, team_id: UUID) -> tuple["TeamEvent", UUID]:
        # rotate 는 Team 엔티티가 없어 두 번째 원소는 team_id (그 외 팩토리는 entity)
        return cls(_kind=TeamEventKind.ROTATED, _act_entity_id=team_id), team_id

    # #
    # query

    def act(self) -> str:
        return self._kind.value

    def act_entity_name(self) -> str:
        return "team"

    def act_entity_id(self) -> UUID:
        return self._act_entity_id

    def payload(self) -> dict:
        return {"name": self._name} if self._name is not None else {}
