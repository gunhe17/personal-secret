from __future__ import annotations

from uuid import UUID
from dataclasses import dataclass, replace

from personal_secret.api.core.entity import Entity
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.event.entity_name import EntityName
from personal_secret.api.domain.event.entity_action import EntityAction
from personal_secret.api.domain.event.payload import Payload
from personal_secret.api.domain.event.status import Status
from personal_secret.api.domain.event.succeeded_at import SucceededAt
from personal_secret.api.domain.event.failed_at import FailedAt
from personal_secret.api.domain.event.error import Error


@dataclass(frozen=True, kw_only=True)
class Event(Entity):
    entity_name: EntityName
    entity_action: EntityAction
    entity_id: UUID
    payload: Payload
    status: Status
    # team_id 는 테넌트 격리 — 시스템 이벤트(팀 무관)면 None
    team_id: UUID | None = None
    sequence: int | None = None
    succeeded_at: SucceededAt | None = None
    failed_at: FailedAt | None = None
    error: Error | None = None

    # #
    # factory

    @classmethod
    @typecheck
    def new(
        cls,
        *,
        id: UUID,
        entity_name: EntityName,
        entity_action: EntityAction,
        entity_id: UUID,
        payload: Payload,
        team_id: UUID | None = None,
    ) -> "Event":
        return cls(
            id=id,
            entity_name=entity_name,
            entity_action=entity_action,
            entity_id=entity_id,
            payload=payload,
            team_id=team_id,
            status=Status.pending(),
            by_factory=True,
        )

    # #
    # transition

    def succeed(self, *, at: SucceededAt) -> "Event":
        return replace(
            self,
            status=Status.succeeded(),
            succeeded_at=at,
            by_factory=True,
        )

    def fail(self, *, at: FailedAt, error: Error) -> "Event":
        return replace(
            self,
            status=Status.failed(),
            failed_at=at,
            error=error,
            by_factory=True,
        )

    # #
    # query

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "sequence": self.sequence,
            "team_id": (
                str(self.team_id) if self.team_id else None
            ),
            "entity_name": self.entity_name.to_str(),
            "entity_action": self.entity_action.to_str(),
            "entity_id": str(self.entity_id),
            "payload": self.payload.to_dict(),
            "status": self.status.to_str(),
            "error": (
                self.error.to_str() if self.error else None
            ),
            "succeeded_at": (
                self.succeeded_at.to_str() if self.succeeded_at else None
            ),
            "failed_at": (
                self.failed_at.to_str() if self.failed_at else None
            ),
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }

    def to_model(self) -> dict:
        return {
            "id": self.id,
            "team_id": self.team_id,
            "entity_name": self.entity_name.to_str(),
            "entity_action": self.entity_action.to_str(),
            "entity_id": self.entity_id,
            "payload": self.payload.to_dict(),
            "status": self.status.to_str(),
            "error": (
                self.error.to_str() if self.error else None
            ),
            "succeeded_at": (
                self.succeeded_at.to_datetime() if self.succeeded_at else None
            ),
            "failed_at": (
                self.failed_at.to_datetime() if self.failed_at else None
            ),
        }
