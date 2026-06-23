from __future__ import annotations

from dataclasses import dataclass

from personal_secret.api.core.value_object import ValueObject
from personal_secret.api.domain.common.exception import InvalidError, InvalidFormatError


@dataclass(frozen=True, kw_only=True)
class Attempts(ValueObject):
    _value: int

    # #
    # factory

    @classmethod
    def from_int(cls, value) -> "Attempts":
        # type
        if not isinstance(value, int) or isinstance(value, bool):
            raise InvalidError("Attempts")

        # range
        if value < 0:
            raise InvalidFormatError("Attempts")

        return cls(_value=value, by_factory=True)

    # #
    # query

    def to_int(self) -> int:
        return self._value

    def increment(self) -> "Attempts":
        return Attempts.from_int(self._value + 1)
