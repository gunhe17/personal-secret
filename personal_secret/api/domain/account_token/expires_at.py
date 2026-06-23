from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass

from personal_secret.api.core.value_object import ValueObject
from personal_secret.api.domain.common.exception import InvalidError


@dataclass(frozen=True, kw_only=True)
class ExpiresAt(ValueObject):
    _value: datetime

    # #
    # factory

    @classmethod
    def from_datetime(cls, value) -> "ExpiresAt":
        # type
        if not isinstance(value, datetime):
            raise InvalidError("ExpiresAt")

        return cls(_value=value, by_factory=True)

    # #
    # query

    def to_str(self) -> str:
        return self._value.isoformat()

    def to_datetime(self) -> datetime:
        return self._value

    def is_past(self, *, now: datetime) -> bool:
        return self._value <= now
