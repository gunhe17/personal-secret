from __future__ import annotations

import base64
from dataclasses import dataclass

from personal_secret.api.core.value_object import ValueObject
from personal_secret.api.domain.common.exception import InvalidError, InvalidFormatError


@dataclass(frozen=True, kw_only=True)
class PersonalLockedKey(ValueObject):
    _value: str

    # #
    # factory

    @classmethod
    def from_str(cls, value) -> "PersonalLockedKey":
        # type
        if not isinstance(value, str):
            raise InvalidError("PersonalLockedKey")

        # format
        try:
            base64.b64decode(value, validate=True)
        except (ValueError, TypeError):
            raise InvalidFormatError("PersonalLockedKey")

        return cls(_value=value, by_factory=True)

    # #
    # query

    def to_str(self) -> str:
        return self._value
