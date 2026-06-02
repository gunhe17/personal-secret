from __future__ import annotations

from dataclasses import dataclass

from personal_secret.api.core.value_object import ValueObject
from personal_secret.api.domain.common.exception import InvalidError, InvalidFormatError


@dataclass(frozen=True, kw_only=True)
class Kind(ValueObject):
    _value: str

    # hint
    _allowed_list: tuple[str, ...] = (
        "secret.created",
        "secret.updated",
        "secret.deleted",
        "vault.initialized",
    )

    # #
    # factory

    @classmethod
    def from_str(cls, value) -> "Kind":
        # type
        if not isinstance(value, str):
            raise InvalidError("Kind")

        # format
        if value not in cls._allowed_list:
            raise InvalidFormatError("Kind")

        return cls(_value=value, by_factory=True)

    # #
    # query

    def to_str(self) -> str:
        return self._value
