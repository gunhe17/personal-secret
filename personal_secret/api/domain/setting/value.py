from __future__ import annotations

from dataclasses import dataclass

from personal_secret.api.core.value_object import ValueObject
from personal_secret.api.domain.common.exception import InvalidError, InvalidFormatError


@dataclass(frozen=True, kw_only=True)
class Value(ValueObject):
    # scalar(str/int/float/bool) 또는 list — dict/None 등 중첩 구조는 불가
    _value: str | int | float | bool | tuple

    # hint
    _scalar_types: tuple = (str, int, float, bool)

    # #
    # factory

    @classmethod
    def from_json(cls, value) -> "Value":
        # type — scalar 는 그대로
        if isinstance(value, cls._scalar_types):
            return cls(_value=value, by_factory=True)

        # format — list 는 scalar 원소만 (중첩 거부), 불변성 위해 tuple 보관
        if isinstance(value, list):
            for item in value:
                if not isinstance(item, cls._scalar_types):
                    raise InvalidFormatError("Value")
            return cls(_value=tuple(value), by_factory=True)

        # 그 외(dict/None 등) 거부
        raise InvalidError("Value")

    # #
    # query

    def to_json(self):
        # list 는 tuple 로 보관 → 복원
        if isinstance(self._value, tuple):
            return list(self._value)

        return self._value
