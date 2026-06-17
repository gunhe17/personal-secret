from __future__ import annotations

import re
from dataclasses import dataclass

from personal_secret.api.core.value_object import ValueObject
from personal_secret.api.domain.common.exception import InvalidError, InvalidFormatError


@dataclass(frozen=True, kw_only=True)
class Email(ValueObject):
    _value: str

    # hint
    _pattern: str = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    _max_length: int = 254

    # #
    # factory

    @classmethod
    def from_str(cls, value) -> "Email":
        # type
        if not isinstance(value, str):
            raise InvalidError("Email")

        # normalize
        normalized = value.strip().lower()

        # length
        if not (0 < len(normalized) <= cls._max_length):
            raise InvalidFormatError("Email")

        # format
        if not re.match(cls._pattern, normalized):
            raise InvalidFormatError("Email")

        return cls(_value=normalized, by_factory=True)

    # #
    # query

    def to_str(self) -> str:
        return self._value
