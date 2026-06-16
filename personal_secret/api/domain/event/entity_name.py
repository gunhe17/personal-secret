from __future__ import annotations

from dataclasses import dataclass

from personal_secret.api.core.value_object import ValueObject
from personal_secret.api.domain.common.exception import InvalidError, InvalidFormatError


@dataclass(frozen=True, kw_only=True)
class EntityName(ValueObject):
    _value: str

    # hint
    _allowed_list: tuple[str, ...] = ("secret", "team", "account_team", "account", "token", "setting")

    # #
    # factory

    @classmethod
    def from_str(cls, value) -> "EntityName":
        # type
        if not isinstance(value, str):
            raise InvalidError("EntityName")

        # format
        if value not in cls._allowed_list:
            raise InvalidFormatError("EntityName")

        return cls(_value=value, by_factory=True)

    # #
    # query

    def to_str(self) -> str:
        return self._value
