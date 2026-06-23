from __future__ import annotations

from uuid import UUID
from datetime import datetime
from dataclasses import dataclass, replace

from personal_secret.api.core.entity import Entity
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.event.event.event_name import EventName
from personal_secret.api.domain.event.event.dispatch_status import DispatchStatus
from personal_secret.api.domain.event.event.attempts import Attempts
from personal_secret.api.domain.event.event.errors import Errors


@dataclass(frozen=True, kw_only=True)
class Event(Entity):
    name: EventName
    status: DispatchStatus
    attempts: Attempts
    errors: Errors
    claimed_at: datetime | None = None
    succeeded_at: datetime | None = None
    failed_at: datetime | None = None

    # #
    # factory

    @classmethod
    @typecheck
    def new(cls, *, id: UUID, name: EventName) -> "Event":
        event = cls(
            id=id,
            name=name,
            status=DispatchStatus.pending(),
            attempts=Attempts.from_int(0),
            errors=Errors.from_list([]),
            by_factory=True,
        )
        return event

    # #
    # transition

    def succeed(self, *, at: datetime) -> "Event":
        return replace(
            self,
            status=DispatchStatus.succeeded(),
            succeeded_at=at,
            by_factory=True,
        )

    def fail(self, *, at: datetime, error: str, max_attempts: int) -> "Event":
        attempted = self.attempts.increment()
        recorded = self.errors.append(error)

        # cap
        if attempted.to_int() >= max_attempts:
            return replace(
                self,
                status=DispatchStatus.failed(),
                attempts=attempted,
                errors=recorded,
                failed_at=at,
                by_factory=True,
            )

        return replace(
            self,
            status=DispatchStatus.pending(),
            attempts=attempted,
            errors=recorded,
            by_factory=True,
        )

    # #
    # query

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name.to_str(),
            "status": self.status.to_str(),
            "attempts": self.attempts.to_int(),
            "errors": self.errors.to_list(),
            "claimed_at": (
                self.claimed_at.isoformat() if self.claimed_at else None
            ),
            "succeeded_at": (
                self.succeeded_at.isoformat() if self.succeeded_at else None
            ),
            "failed_at": (
                self.failed_at.isoformat() if self.failed_at else None
            ),
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
            "deleted_at": (
                self.deleted_at.isoformat() if self.deleted_at else None
            ),
        }

    def to_model(self) -> dict:
        return {
            "id": self.id,
            "name": self.name.to_str(),
            "status": self.status.to_str(),
            "attempts": self.attempts.to_int(),
            "errors": self.errors.to_list(),
            "claimed_at": self.claimed_at,
            "succeeded_at": self.succeeded_at,
            "failed_at": self.failed_at,
        }
