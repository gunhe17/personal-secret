from __future__ import annotations

from uuid import UUID
from dataclasses import dataclass

from personal_secret.api.core.entity import Entity
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.event.act import Act
from personal_secret.api.domain.event.entity_name import EntityName
from personal_secret.api.domain.event.payload import Payload


@dataclass(frozen=True, kw_only=True)
class Event(Entity):
    act: Act
    act_entity_name: EntityName
    act_entity_id: UUID
    payload: Payload
    act_group_id: UUID
    actor_id: UUID | None = None
    actor_team_id: UUID | None = None
    sequence: int | None = None

    # #
    # factory

    @classmethod
    @typecheck
    def new(
        cls,
        *,
        id: UUID,
        act: Act,
        act_entity_name: EntityName,
        act_entity_id: UUID,
        payload: Payload,
        act_group_id: UUID,
        actor_id: UUID | None = None,
        actor_team_id: UUID | None = None,
    ) -> "Event":
        return cls(
            id=id,
            act=act,
            act_entity_name=act_entity_name,
            act_entity_id=act_entity_id,
            payload=payload,
            act_group_id=act_group_id,
            actor_id=actor_id,
            actor_team_id=actor_team_id,
            by_factory=True,
        )

    # #
    # query

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "sequence": self.sequence,
            "act_group_id": str(self.act_group_id),
            "actor_id": (
                str(self.actor_id) if self.actor_id else None
            ),
            "actor_team_id": (
                str(self.actor_team_id) if self.actor_team_id else None
            ),
            "act": self.act.to_str(),
            "act_entity_name": self.act_entity_name.to_str(),
            "act_entity_id": str(self.act_entity_id),
            "payload": self.payload.to_dict(),
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }

    def to_model(self) -> dict:
        return {
            "id": self.id,
            "act_group_id": self.act_group_id,
            "actor_id": self.actor_id,
            "actor_team_id": self.actor_team_id,
            "act": self.act.to_str(),
            "act_entity_name": self.act_entity_name.to_str(),
            "act_entity_id": self.act_entity_id,
            "payload": self.payload.to_dict(),
        }
