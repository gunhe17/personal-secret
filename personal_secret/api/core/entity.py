from __future__ import annotations

import uuid
from dataclasses import InitVar, dataclass, field
from datetime import datetime

from personal_secret.api.core.exception import DevelopError


@dataclass(frozen=True, kw_only=True)
class Entity:
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    # audit
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None

    by_factory: InitVar[bool] = False

    def __post_init__(self, by_factory: bool):
        if not by_factory:
            raise DevelopError(
                message=f"{type(self).__name__} 팩토리로만 생성 가능 (허용: new/with_*)",
                code=500,
            )
