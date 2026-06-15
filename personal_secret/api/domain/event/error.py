from __future__ import annotations

from dataclasses import dataclass

from personal_secret.api.core.value_object import ValueObject
from personal_secret.api.domain.common.exception import InvalidError


@dataclass(frozen=True, kw_only=True)
class Error(ValueObject):
    _value: str

    # hint
    _max_length: int = 2000

    # #
    # factory

    @classmethod
    def from_str(cls, value) -> "Error":
        # type
        if not isinstance(value, str):
            raise InvalidError("Error")

        # cap (핸들러 예외 메시지는 길 수 있어 자른다)
        normalized = value.strip()[: cls._max_length]
        return cls(_value=normalized, by_factory=True)

    # #
    # query

    def to_str(self) -> str:
        return self._value
