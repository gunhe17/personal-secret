from __future__ import annotations

from abc import ABC, abstractmethod


# #
# hash

class Hash(ABC):
    @abstractmethod
    def hash(self, *, value: str) -> str: ...

    @abstractmethod
    def verify(self, *, hash: str, value: str) -> bool: ...
