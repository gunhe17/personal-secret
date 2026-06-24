from __future__ import annotations

import copy
from uuid import UUID
from dataclasses import dataclass

from personal_secret.api.core.value_object import ValueObject
from personal_secret.api.domain.common.exception import InvalidError


@dataclass(frozen=True, kw_only=True)
class Attempts(ValueObject):
    _value: dict

    # #
    # factory

    @classmethod
    def from_dict(cls, value) -> "Attempts":
        # type
        if not isinstance(value, dict):
            raise InvalidError("Attempts")

        # 외부에서 들고 있는 dict 로 내부가 바뀌지 않게 방어적으로 깊은 복사한다
        return cls(_value=copy.deepcopy(value), by_factory=True)

    @classmethod
    def empty(cls) -> "Attempts":
        return cls.from_dict({})

    # #
    # query

    def to_dict(self) -> dict:
        return copy.deepcopy(self._value)

    def is_done(self, *, reaction: str, atomic_id: UUID) -> bool:
        unit = self._value.get(reaction, {}).get(str(atomic_id))
        return unit is not None and unit.get("status") == "succeeded"

    def dispatch_count(self) -> int:
        return self._value.get("_dispatch", {}).get("count", 0)

    # #
    # command

    def record_success(self, *, reaction: str, atomic_id: UUID) -> "Attempts":
        return self._record_unit(reaction=reaction, atomic_id=atomic_id, status="succeeded", error=None)

    def record_failure(self, *, reaction: str, atomic_id: UUID, error: str) -> "Attempts":
        return self._record_unit(reaction=reaction, atomic_id=atomic_id, status="failed", error=error)

    def record_dispatch_failure(self, *, error: str) -> "Attempts":
        ledger = copy.deepcopy(self._value)
        prev = ledger.get("_dispatch", {})
        ledger["_dispatch"] = {"count": prev.get("count", 0) + 1, "error": error}
        return Attempts.from_dict(ledger)

    def _record_unit(self, *, reaction, atomic_id, status, error) -> "Attempts":
        ledger = copy.deepcopy(self._value)
        units = ledger.setdefault(reaction, {})
        key = str(atomic_id)
        unit = {
            "status": status,
            "count": units.get(key, {}).get("count", 0) + 1,
        }
        if error is not None:
            unit["error"] = error
        units[key] = unit
        return Attempts.from_dict(ledger)
