from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from personal_secret.api.core.event import Event
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.vault.vault import Vault


class VaultEventKind(Enum):
    INITIALIZED = "vault.initialized"


@dataclass(frozen=True, kw_only=True)
class VaultEvent(Event):
    _kind: VaultEventKind
    vault: Vault

    # #
    # factory

    @classmethod
    @typecheck
    def initialized(cls, *, vault: Vault) -> tuple["VaultEvent", Vault]:
        return cls(_kind=VaultEventKind.INITIALIZED, vault=vault), vault

    # #
    # query

    def kind(self) -> str:
        return self._kind.value

    def entity_type(self) -> str:
        return "Vault"

    def entity_id(self) -> UUID:
        return self.vault.id

    def to_dict(self) -> dict:
        return {
            "kind": self._kind.value,
            "vault_id": str(self.vault.id),
        }
