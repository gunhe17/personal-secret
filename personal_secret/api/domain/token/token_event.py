from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from personal_secret.api.core.event import Event
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.token.token import Token


class TokenEventKind(Enum):
    CREATED = "created"


@dataclass(frozen=True, kw_only=True)
class TokenEvent(Event):
    _kind: TokenEventKind
    token: Token

    # #
    # factory

    @classmethod
    @typecheck
    def created(cls, *, token: Token) -> tuple["TokenEvent", Token]:
        return cls(_kind=TokenEventKind.CREATED, token=token), token

    # #
    # query

    def act(self) -> str:
        return self._kind.value

    def act_entity_name(self) -> str:
        return "token"

    def act_entity_id(self) -> UUID:
        return self.token.id

    def payload(self) -> dict:
        return {"account_id": str(self.token.account_id)}
