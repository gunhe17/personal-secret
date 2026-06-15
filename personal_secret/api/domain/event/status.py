from __future__ import annotations

from dataclasses import dataclass

from personal_secret.api.core.value_object import ValueObject
from personal_secret.api.domain.common.exception import InvalidError, InvalidFormatError


@dataclass(frozen=True, kw_only=True)
class Status(ValueObject):
    _value: str

    # hint
    _allowed_list: tuple[str, ...] = ("pending", "succeeded", "failed")

    # #
    # factory

    @classmethod
    def from_str(cls, value) -> "Status":
        # type
        if not isinstance(value, str):
            raise InvalidError("Status")

        # format
        if value not in cls._allowed_list:
            raise InvalidFormatError("Status")

        return cls(_value=value, by_factory=True)

    @classmethod
    def pending(cls) -> "Status":
        return cls(_value="pending", by_factory=True)

    @classmethod
    def succeeded(cls) -> "Status":
        return cls(_value="succeeded", by_factory=True)

    @classmethod
    def failed(cls) -> "Status":
        return cls(_value="failed", by_factory=True)

    # #
    # query

    def to_str(self) -> str:
        return self._value
