from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Self

from pydantic import BaseModel


# #
# input

class In(BaseModel):
    _source_event: ClassVar[str]

    @classmethod
    def from_events(cls, events: list) -> Self:
        event = next(
            event
            for event in events
            if event.to_name() == cls._source_event
        )
        payload = event.payload.to_dict()
        return cls(**{
            name: payload[name] for name in cls.model_fields
        })


# #
# output

@dataclass(frozen=True, kw_only=True)
class Out:
    data: dict | list
    event: list | None
    
    def to_dict(self) -> dict:
        return {
            "data": self.data,
            "event": self.event,
        }
