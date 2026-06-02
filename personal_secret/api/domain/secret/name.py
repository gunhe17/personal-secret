from __future__ import annotations

import re
from dataclasses import dataclass

from personal_secret.api.core.value_object import ValueObject
from personal_secret.api.domain.common.exception import InvalidError, InvalidFormatError


@dataclass(frozen=True, kw_only=True)
class Name(ValueObject):
    _value: str

    # hint
    _pattern: str = r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
    _max_length: int = 128

    # #
    # factory

    @classmethod
    def from_str(cls, value) -> "Name":
        # type
        if not isinstance(value, str):
            raise InvalidError("Name")

        # normalize
        normalized = value.strip()

        # length
        if not (0 < len(normalized) <= cls._max_length):
            raise InvalidFormatError("Name")

        # format
        if not re.match(cls._pattern, normalized):
            raise InvalidFormatError("Name")

        return cls(_value=normalized, by_factory=True)

    # #
    # query

    def to_str(self) -> str:
        return self._value
