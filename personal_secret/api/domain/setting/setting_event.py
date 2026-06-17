from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from personal_secret.api.core.event import Event
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.setting.setting import Setting


class SettingEventKind(Enum):
    UPDATED = "updated"
    READ = "read"


@dataclass(frozen=True, kw_only=True)
class SettingEvent(Event):
    _kind: SettingEventKind
    setting: Setting

    # #
    # factory

    @classmethod
    @typecheck
    def updated(cls, *, setting: Setting) -> tuple["SettingEvent", Setting]:
        return cls(_kind=SettingEventKind.UPDATED, setting=setting), setting

    @classmethod
    @typecheck
    def read(cls, *, setting: Setting) -> tuple["SettingEvent", Setting]:
        return cls(_kind=SettingEventKind.READ, setting=setting), setting

    @classmethod
    @typecheck
    def read_many(cls, *, settings: list) -> list[tuple["SettingEvent", Setting]]:
        return [
            (
                cls(_kind=SettingEventKind.READ, setting=setting), setting
            )
            for setting in settings
        ]

    # #
    # query

    def act(self) -> str:
        return self._kind.value

    def act_entity_name(self) -> str:
        return "setting"

    def act_entity_id(self) -> UUID:
        return self.setting.id

    def payload(self) -> dict:
        return {"key": self.setting.key.to_str()}
