from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from personal_secret.api.core.event import Event
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.secret.secret import Secret


class SecretEventKind(Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    READ = "read"


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
    def updated(cls, *, secret: Secret) -> tuple["SecretEvent", Secret]:
        return cls(_kind=SecretEventKind.UPDATED, secret=secret), secret

    @classmethod
    @typecheck
    def deleted(cls, *, secret: Secret) -> tuple["SecretEvent", Secret]:
        return cls(_kind=SecretEventKind.DELETED, secret=secret), secret

    @classmethod
    @typecheck
    def read(cls, *, secret: Secret) -> tuple["SecretEvent", Secret]:
        return cls(_kind=SecretEventKind.READ, secret=secret), secret

    @classmethod
    @typecheck
    def read_many(cls, *, secrets: list) -> list[tuple["SecretEvent", Secret]]:
        return [
            (cls(_kind=SecretEventKind.READ, secret=secret), secret)
            for secret in secrets
        ]

    # #
    # query

    def act(self) -> str:
        return self._kind.value

    def act_entity_name(self) -> str:
        return "secret"

    def act_entity_id(self) -> UUID:
        return self.secret.id

    def payload(self) -> dict:
        # 평문 식별자만 — value(암호문)는 절대 싣지 않는다
        return {
            "domain": self.secret.domain.to_str(),
            "service": self.secret.service.to_str(),
            "project": self.secret.project.to_str(),
            "field": self.secret.field.to_str(),
        }
