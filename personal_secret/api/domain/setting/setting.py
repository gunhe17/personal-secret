from __future__ import annotations

from dataclasses import dataclass, replace

from personal_secret.api.core.entity import Entity
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.setting.key import Key
from personal_secret.api.domain.setting.value import Value


@dataclass(frozen=True, kw_only=True)
class Setting(Entity):
    key: Key
    value: Value

    # #
    # factory

    @classmethod
    @typecheck
    def new(cls, *, key: Key, value: Value) -> "Setting":
        setting = cls(key=key, value=value, by_factory=True)
        return setting

    # #
    # update

    def with_value(self, value: Value) -> "Setting":
        return replace(self, value=value, by_factory=True)

    # #
    # query

    def to_dict(self):
        return {
            "id": str(self.id),
            "key": self.key.to_str(),
            "value": self.value.to_json(),
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
            "key": self.key.to_str(),
            "value": self.value.to_json(),
        }
