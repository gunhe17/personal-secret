from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from personal_secret.api.core.event import Event
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.account.account import Account


class AccountEventKind(Enum):
    CREATED = "created"
    READ = "read"


@dataclass(frozen=True, kw_only=True)
class AccountEvent(Event):
    _kind: AccountEventKind
    account: Account

    # #
    # factory

    @classmethod
    @typecheck
    def created(cls, *, account: Account) -> tuple["AccountEvent", Account]:
        return cls(_kind=AccountEventKind.CREATED, account=account), account

    @classmethod
    @typecheck
    def read(cls, *, account: Account) -> tuple["AccountEvent", Account]:
        return cls(_kind=AccountEventKind.READ, account=account), account

    # #
    # query

    def act(self) -> str:
        return self._kind.value

    def act_entity_name(self) -> str:
        return "account"

    def act_entity_id(self) -> UUID:
        return self.account.id

    def payload(self) -> dict:
        return {"email": self.account.email.to_str()}
