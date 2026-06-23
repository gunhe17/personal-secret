from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from personal_secret.api.core.behavior import Context


# #
# event

@dataclass(frozen=True)
class EventGroupContext(Context):
    event_group_id: UUID

    @classmethod
    async def setup(
        cls,
    ) -> EventGroupContext:
        return EventGroupContext(
            event_group_id=uuid4()
        )