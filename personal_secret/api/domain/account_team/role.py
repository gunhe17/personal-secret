from __future__ import annotations

from dataclasses import dataclass

from personal_secret.api.core.value_object import ValueObject
from personal_secret.api.domain.common.exception import InvalidError, InvalidFormatError


@dataclass(frozen=True, kw_only=True)
class Role(ValueObject):
    _value: str

    # hint
    _allowed_list: tuple[str, ...] = ("owner", "member")

    # #
    # factory

    @classmethod
    def from_str(cls, value) -> "Role":
        # type
        if not isinstance(value, str):
            raise InvalidError("Role")

        # format
        if value not in cls._allowed_list:
            raise InvalidFormatError("Role")

        return cls(_value=value, by_factory=True)

    @classmethod
    def owner(cls) -> "Role":
        return cls.from_str("owner")

    # #
    # query

    def to_str(self) -> str:
        return self._value

    def is_owner(self) -> bool:
        return self._value == "owner"
