from __future__ import annotations

from dataclasses import dataclass

from personal_secret.api.core.value_object import ValueObject
from personal_secret.api.domain.common.exception import InvalidError, InvalidFormatError


@dataclass(frozen=True, kw_only=True)
class Errors(ValueObject):
    _items: tuple[str, ...]

    # #
    # factory

    @classmethod
    def from_list(cls, value) -> "Errors":
        # type
        if not isinstance(value, list):
            raise InvalidError("Errors")

        # format
        for item in value:
            if not isinstance(item, str):
                raise InvalidFormatError("Errors")

        return cls(_items=tuple(value), by_factory=True)

    # #
    # query

    def to_list(self) -> list:
        return list(self._items)

    def append(self, message: str) -> "Errors":
        return Errors.from_list([*self._items, message])
