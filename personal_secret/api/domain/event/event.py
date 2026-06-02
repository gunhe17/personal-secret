from __future__ import annotations

from uuid import UUID
from dataclasses import dataclass

from personal_secret.api.core.entity import Entity
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.event.kind import Kind
from personal_secret.api.domain.event.entity_type import EntityType


@dataclass(frozen=True, kw_only=True)
class Event(Entity):
    kind: Kind
    entity_type: EntityType
    entity_id: UUID

    # #
    # factory

    @classmethod
    @typecheck
    def new(
        cls,
        *,
        id: UUID,
        kind: Kind,
        entity_type: EntityType,
        entity_id: UUID,
    ) -> "Event":
        # id를 받는다 — 이벤트 identity는 발생 시점(마커 created)에 확정됨
        return cls(
            id=id,
            kind=kind,
            entity_type=entity_type,
            entity_id=entity_id,
            by_factory=True,
        )

    # #
    # query

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "kind": self.kind.to_str(),
            "entity_type": self.entity_type.to_str(),
            "entity_id": str(self.entity_id),
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }

    def to_model(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind.to_str(),
            "entity_type": self.entity_type.to_str(),
            "entity_id": self.entity_id,
        }
