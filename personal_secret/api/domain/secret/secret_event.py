from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from personal_secret.api.core.event import Event
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.secret.secret import Secret


class SecretEventKind(Enum):
    CREATED = "secret.created"
    UPDATED = "secret.updated"
    DELETED = "secret.deleted"


@dataclass(frozen=True, kw_only=True)
class SecretEvent(Event):
    _kind: SecretEventKind
    secret: Secret

    # #
    # factory

    @classmethod
    @typecheck
    def created(cls, *, secret: Secret) -> tuple["SecretEvent", Secret]:
        return cls(_kind=SecretEventKind.CREATED, secret=secret), secret

    @classmethod
    @typecheck
    def updated(cls, *, secret: Secret) -> "SecretEvent":
        return cls(_kind=SecretEventKind.UPDATED, secret=secret)

    @classmethod
    @typecheck
    def deleted(cls, *, secret: Secret) -> tuple["SecretEvent", Secret]:
        return cls(_kind=SecretEventKind.DELETED, secret=secret), secret

    # #
    # query

    def kind(self) -> str:
        return self._kind.value

    def entity_type(self) -> str:
        return "Secret"

    def entity_id(self) -> UUID:
        return self.secret.id

    def to_dict(self) -> dict:
        return {
            "kind": self._kind.value,
            "secret_id": str(self.secret.id),
        }
