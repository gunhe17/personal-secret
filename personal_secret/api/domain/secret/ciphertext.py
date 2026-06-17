from __future__ import annotations

import base64
from dataclasses import dataclass

from personal_secret.api.core.value_object import ValueObject
from personal_secret.api.domain.common.exception import InvalidError, InvalidFormatError


@dataclass(frozen=True, kw_only=True)
class Ciphertext(ValueObject):
    # nonce + ciphertext를 합친 불투명 blob (포맷은 crypto가 소유)
    _value: bytes

    # #
    # factory

    @classmethod
    def from_bytes(cls, value: bytes) -> "Ciphertext":
        # type
        if not isinstance(value, bytes):
            raise InvalidError("Ciphertext")

        return cls(_value=value, by_factory=True)

    @classmethod
    def from_str(cls, value) -> "Ciphertext":
        # type
        if not isinstance(value, str):
            raise InvalidError("Ciphertext")

        # format
        try:
            decoded = base64.b64decode(value, validate=True)
        except (ValueError, TypeError):
            raise InvalidFormatError("Ciphertext")

        return cls(_value=decoded, by_factory=True)

    # #
    # query

    def to_bytes(self) -> bytes:
        return self._value

    def to_str(self) -> str:
        return base64.b64encode(self._value).decode("ascii")
