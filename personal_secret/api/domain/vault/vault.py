from __future__ import annotations

from dataclasses import dataclass

from personal_secret.api.core.entity import Entity
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.vault.salt import Salt
from personal_secret.api.domain.vault.wrapped_dek import WrappedDek


@dataclass(frozen=True, kw_only=True)
class Vault(Entity):
    salt: Salt
    wrapped_dek: WrappedDek

    # #
    # factory

    @classmethod
    @typecheck
    def new(cls, *, salt: Salt, wrapped_dek: WrappedDek) -> "Vault":
        vault = cls(salt=salt, wrapped_dek=wrapped_dek, by_factory=True)
        return vault

    # #
    # query

    def to_dict(self):
        # salt/wrapped_dek은 암호 자료 — API 응답에 노출하지 않는다 (초기화 메타만)
        return {
            "id": str(self.id),
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
            "salt": self.salt.to_str(),
            "wrapped_dek": self.wrapped_dek.to_str(),
        }
