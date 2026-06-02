from __future__ import annotations

from dataclasses import InitVar, dataclass

from personal_secret.api.core.exception import DevelopError


@dataclass(frozen=True, kw_only=True)
class ValueObject:
    by_factory: InitVar[bool] = False

    def __post_init__(self, by_factory: bool):
        if not by_factory:
            raise DevelopError(
                message=f"{type(self).__name__}: 팩토리로만 생성할 수 있습니다.",
                code=500,
            )
