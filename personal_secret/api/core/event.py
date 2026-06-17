from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4


# #
# DomainEvent

@dataclass(frozen=True, kw_only=True)
class Event:
    _id: UUID = field(default_factory=uuid4)

    def id(self) -> UUID:
        return self._id
