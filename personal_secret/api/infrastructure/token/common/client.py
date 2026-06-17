from __future__ import annotations

from abc import ABC, abstractmethod


# #
# token

class Token(ABC):
    @abstractmethod
    def generate(self) -> str: ...
