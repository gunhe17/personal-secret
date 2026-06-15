from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass

from personal_secret.api.core.value_object import ValueObject
from personal_secret.api.domain.common.exception import InvalidError


@dataclass(frozen=True, kw_only=True)
class SucceededAt(ValueObject):
    _value: datetime

    # #
    # factory

    @classmethod
    def from_datetime(cls, value) -> "SucceededAt":
        # type
        if not isinstance(value, datetime):
            raise InvalidError("SucceededAt")

        return cls(_value=value, by_factory=True)

    # #
    # query

    def to_str(self) -> str:
        return self._value.isoformat()

    def to_datetime(self) -> datetime:
        return self._value
