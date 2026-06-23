from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from personal_secret.api.core.event import Event
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.account_token.account_token import AccountToken


class AccountTokenEventKind(Enum):
    CREATED = "created"


@dataclass(frozen=True, kw_only=True)
class AccountTokenEvent(Event):
    _kind: AccountTokenEventKind
    account_token: AccountToken

    # #
    # factory

    @classmethod
    @typecheck
    def created(cls, *, account_token: AccountToken) -> tuple["AccountTokenEvent", AccountToken]:
        return cls(_kind=AccountTokenEventKind.CREATED, account_token=account_token), account_token

    # #
    # query

    def act(self) -> str:
        return self._kind.value

    def act_entity_name(self) -> str:
        return "account_token"

    def act_entity_id(self) -> UUID:
        return self.account_token.id

    def payload(self) -> dict:
        return {"account_id": str(self.account_token.account_id)}
