from __future__ import annotations

import os
from abc import ABC, abstractmethod


# #
# cli

class CliConfig(ABC):
    @property
    @abstractmethod
    def API_BASE_URL(self) -> str: ...

    @property
    @abstractmethod
    def TOKEN_PATH(self) -> str: ...


class DefaultCliConfig(CliConfig):
    @property
    def API_BASE_URL(self) -> str:
        return os.environ.get("PERSONAL_SECRET_API", "http://127.0.0.1:28200")

    @property
    def TOKEN_PATH(self) -> str:
        return os.environ.get(
            "PERSONAL_SECRET_TOKEN_PATH",
            os.path.expanduser("~/.config/personal-secret/token"),
        )


def get_cli_config() -> CliConfig:
    config = DefaultCliConfig()
    return config
