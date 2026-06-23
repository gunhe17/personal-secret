from __future__ import annotations

from dataclasses import dataclass

from personal_secret.api.core.value_object import ValueObject
from personal_secret.api.domain.common.exception import InvalidError, InvalidFormatError


@dataclass(frozen=True, kw_only=True)
class DispatchStatus(ValueObject):
    _value: str

    # hint
    _allowed_list: tuple[str, ...] = ("pending", "claimed", "succeeded", "failed")

    # #
    # factory

    @classmethod
    def from_str(cls, value) -> "DispatchStatus":
        # type
        if not isinstance(value, str):
            raise InvalidError("DispatchStatus")

        # format
        if value not in cls._allowed_list:
            raise InvalidFormatError("DispatchStatus")

        return cls(_value=value, by_factory=True)

    @classmethod
    def pending(cls) -> "DispatchStatus":
        return cls.from_str("pending")

    @classmethod
    def claimed(cls) -> "DispatchStatus":
        return cls.from_str("claimed")

    @classmethod
    def succeeded(cls) -> "DispatchStatus":
        return cls.from_str("succeeded")

    @classmethod
    def failed(cls) -> "DispatchStatus":
        return cls.from_str("failed")

    # #
    # query

    def to_str(self) -> str:
        return self._value
