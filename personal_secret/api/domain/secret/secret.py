from __future__ import annotations

from dataclasses import dataclass

from personal_secret.api.core.entity import Entity
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.secret.kind import Kind
from personal_secret.api.domain.secret.name import Name
from personal_secret.api.domain.secret.tags import Tags
from personal_secret.api.domain.secret.expires_at import ExpiresAt
from personal_secret.api.domain.secret.ciphertext import Ciphertext


@dataclass(frozen=True, kw_only=True)
class Secret(Entity):
    kind: Kind
    name: Name
    tags: Tags
    ciphertext: Ciphertext
    expires_at: ExpiresAt | None = None

    # #
    # factory

    @classmethod
    @typecheck
    def new(
        cls,
        *,
        kind: Kind,
        name: Name,
        tags: Tags,
        ciphertext: Ciphertext,
        expires_at: ExpiresAt | None = None,
    ) -> "Secret":
        secret = cls(
            kind=kind,
            name=name,
            tags=tags,
            ciphertext=ciphertext,
            expires_at=expires_at,
            by_factory=True,
        )
        return secret

    # #
    # update

    def with_metadata(
        self,
        *,
        name: Name,
        tags: Tags,
        expires_at: ExpiresAt | None,
    ) -> "Secret":
        secret = Secret(
            id=self.id,
            kind=self.kind,
            name=name,
            tags=tags,
            ciphertext=self.ciphertext,
            expires_at=expires_at,
            by_factory=True,
        )
        return secret

    def with_ciphertext(self, ciphertext: Ciphertext) -> "Secret":
        secret = Secret(
            id=self.id,
            kind=self.kind,
            name=self.name,
            tags=self.tags,
            ciphertext=ciphertext,
            expires_at=self.expires_at,
            by_factory=True,
        )
        return secret

    # #
    # query

    def to_dict(self):
        return {
            "id": str(self.id),
            "kind": self.kind.to_str(),
            "name": self.name.to_str(),
            "tags": self.tags.to_list(),
            "expires_at": (
                self.expires_at.to_str() if self.expires_at else None
            ),
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
            "deleted_at": (
                self.deleted_at.isoformat() if self.deleted_at else None
            ),
        }

    def to_model(self):
        return {
            "id": self.id,
            "kind": self.kind.to_str(),
            "name": self.name.to_str(),
            "tags": self.tags.to_list(),
            "ciphertext": self.ciphertext.to_str(),
            "expires_at": (
                self.expires_at.to_datetime() if self.expires_at else None
            ),
        }
