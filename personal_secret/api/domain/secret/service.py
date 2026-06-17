from __future__ import annotations

import re
from dataclasses import dataclass

from personal_secret.api.core.value_object import ValueObject
from personal_secret.api.domain.common.exception import InvalidError, InvalidFormatError


@dataclass(frozen=True, kw_only=True)
class Service(ValueObject):
    _value: str

    # hint
    _pattern: str = r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
    _max_length: int = 128

    # #
    # factory

    @classmethod
    def from_str(cls, value) -> "Service":
        # type
        if not isinstance(value, str):
            raise InvalidError("Service")

        # normalize
        normalized = value.strip()

        # length
        if not (0 < len(normalized) <= cls._max_length):
            raise InvalidFormatError("Service")

        # format
        if not re.match(cls._pattern, normalized):
            raise InvalidFormatError("Service")

        return cls(_value=normalized, by_factory=True)

    # #
    # query

    def to_str(self) -> str:
        return self._value
