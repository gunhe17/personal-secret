from __future__ import annotations

from dataclasses import dataclass

from personal_secret.api.core.value_object import ValueObject
from personal_secret.api.domain.common.exception import InvalidError, InvalidFormatError


@dataclass(frozen=True, kw_only=True)
class TeamName(ValueObject):
    _value: str

    # hint
    _max_length: int = 128

    # #
    # factory

    @classmethod
    def from_str(cls, value) -> "TeamName":
        # type
        if not isinstance(value, str):
            raise InvalidError("TeamName")

        # normalize
        normalized = value.strip()

        # length
        if not (0 < len(normalized) <= cls._max_length):
            raise InvalidFormatError("TeamName")

        return cls(_value=normalized, by_factory=True)

    # #
    # query

    def to_str(self) -> str:
        return self._value
