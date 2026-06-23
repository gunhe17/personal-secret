from __future__ import annotations

import re
from dataclasses import dataclass

from personal_secret.api.core.value_object import ValueObject
from personal_secret.api.domain.common.exception import InvalidError, InvalidFormatError


@dataclass(frozen=True, kw_only=True)
class Fingerprint(ValueObject):
    _value: str  # sha256 hex, 원본 토큰은 저장 안 함

    # hint
    _pattern: str = r"^[0-9a-f]{64}$"

    # #
    # factory

    @classmethod
    def from_str(cls, value) -> "Fingerprint":
        # type
        if not isinstance(value, str):
            raise InvalidError("Fingerprint")

        # format
        if not re.match(cls._pattern, value):
            raise InvalidFormatError("Fingerprint")

        return cls(_value=value, by_factory=True)

    # #
    # query

    def to_str(self) -> str:
        return self._value
