from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from personal_secret.api.core.event import Event
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.account_team.account_team import AccountTeam


class AccountTeamEventKind(Enum):
    CREATED = "created"
    DELETED = "deleted"
    READ = "read"


@dataclass(frozen=True, kw_only=True)
class AccountTeamEvent(Event):
    _kind: AccountTeamEventKind
    membership: AccountTeam

    # #
    # factory

    @classmethod
    @typecheck
    def created(cls, *, membership: AccountTeam) -> tuple["AccountTeamEvent", AccountTeam]:
        return cls(_kind=AccountTeamEventKind.CREATED, membership=membership), membership

    @classmethod
    @typecheck
    def deleted(cls, *, membership: AccountTeam) -> tuple["AccountTeamEvent", AccountTeam]:
        return cls(_kind=AccountTeamEventKind.DELETED, membership=membership), membership

    @classmethod
    @typecheck
    def read(cls, *, membership: AccountTeam) -> tuple["AccountTeamEvent", AccountTeam]:
        return cls(_kind=AccountTeamEventKind.READ, membership=membership), membership

    # #
    # query

    def act(self) -> str:
        return self._kind.value

    def act_entity_name(self) -> str:
        return "account_team"

    def act_entity_id(self) -> UUID:
        return self.membership.id

    def payload(self) -> dict:
        return {
            "account_id": str(self.membership.account_id),
            "role": self.membership.role.to_str(),
        }
