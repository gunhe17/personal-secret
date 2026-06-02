from __future__ import annotations

from dataclasses import dataclass

from personal_secret.api.core.value_object import ValueObject
from personal_secret.api.domain.common.exception import InvalidError, InvalidFormatError


@dataclass(frozen=True, kw_only=True)
class Tags(ValueObject):
    _values: tuple[str, ...]

    # hint
    _max_count: int = 32

    # #
    # factory

    @classmethod
    def from_list(cls, value) -> "Tags":
        # type
        if not isinstance(value, list):
            raise InvalidError("Tags")

        # format
        for tag in value:
            if not isinstance(tag, str) or not tag.strip():
                raise InvalidFormatError("Tags")

        # normalize
        normalized: list[str] = []
        for tag in value:
            stripped = tag.strip()
            if stripped not in normalized:
                normalized.append(stripped)

        # cap
        if len(normalized) > cls._max_count:
            raise InvalidFormatError("Tags")

        return cls(_values=tuple(normalized), by_factory=True)

    # #
    # query

    def to_list(self) -> list[str]:
        return list(self._values)
