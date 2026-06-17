from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from pydantic import BaseModel


# #
# input

class In(BaseModel):
    ...


# #
# output

@dataclass(frozen=True, kw_only=True)
class Out:
    data: dict | list
    event: list | None

    # factory
    @classmethod
    def new(
        cls, 
        *, 
        data: dict | list, 
        event: list | None
    ) -> Self:
        return cls(
            data=data, 
            event=event
        )

    def to_dict(self) -> dict:
        return {
            "data": self.data,
            "event": self.event,
        }
