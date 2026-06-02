from __future__ import annotations

import base64
import builtins
from dataclasses import dataclass

from personal_secret.api.core.value_object import ValueObject
from personal_secret.api.domain.common.exception import InvalidError, InvalidFormatError


@dataclass(frozen=True, kw_only=True)
class Salt(ValueObject):
    # Argon2id KDF salt (랜덤 바이트)
    _value: bytes

    # #
    # factory

    @classmethod
    def from_bytes(cls, *, bytes) -> "Salt":
        # type
        if not isinstance(bytes, builtins.bytes):
            raise InvalidError("Salt")

        return cls(_value=bytes, by_factory=True)

    @classmethod
    def from_str(cls, value) -> "Salt":
        # type
        if not isinstance(value, str):
            raise InvalidError("Salt")

        # format
        try:
            decoded = base64.b64decode(value, validate=True)
        except (ValueError, TypeError):
            raise InvalidFormatError("Salt")

        return cls(_value=decoded, by_factory=True)

    # #
    # query

    def to_bytes(self) -> bytes:
        return self._value

    def to_str(self) -> str:
        return base64.b64encode(self._value).decode("ascii")
