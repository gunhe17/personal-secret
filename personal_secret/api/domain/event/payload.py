from __future__ import annotations

from dataclasses import dataclass

from personal_secret.api.core.value_object import ValueObject
from personal_secret.api.domain.common.exception import InvalidError


@dataclass(frozen=True, kw_only=True)
class Payload(ValueObject):
    _items: tuple[tuple[str, object], ...]

    # #
    # factory

    @classmethod
    def from_dict(cls, value) -> "Payload":
        # type
        if not isinstance(value, dict):
            raise InvalidError("Payload")

        # normalize (방어적 복사 — raw dict는 unhashable → frozen 불변성 보존)
        items = tuple(sorted(value.items(), key=lambda kv: str(kv[0])))
        return cls(_items=items, by_factory=True)

    # #
    # query

    def to_dict(self) -> dict:
        return dict(self._items)
