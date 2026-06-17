from __future__ import annotations

from dataclasses import dataclass

from personal_secret.api.core.value_object import ValueObject
from personal_secret.api.domain.common.exception import InvalidError, InvalidFormatError


@dataclass(frozen=True, kw_only=True)
class LoginVerifier(ValueObject):
    # login_proof 를 서버가 한 번 더 해싱한 검증 대상값 (argon2 PHC). 클라엔 안 나감
    _value: str

    # #
    # factory

    @classmethod
    def from_str(cls, value) -> "LoginVerifier":
        # type
        if not isinstance(value, str):
            raise InvalidError("LoginVerifier")

        # format
        if not value.startswith("$argon2"):
            raise InvalidFormatError("LoginVerifier")

        return cls(_value=value, by_factory=True)

    # #
    # query

    def to_str(self) -> str:
        return self._value
