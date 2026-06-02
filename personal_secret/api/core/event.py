from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4


# #
# DomainEvent

@dataclass(frozen=True, kw_only=True)
class Event:
    # 이벤트 identity — 명명 팩토리(created/updated/...) 호출 시점에 확정
    _id: UUID = field(default_factory=uuid4)

    def id(self) -> UUID:
        return self._id
