from __future__ import annotations

from datetime import datetime
from uuid import UUID
from dataclasses import dataclass

from personal_secret.api.core.entity import Entity
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.account_token.fingerprint import Fingerprint
from personal_secret.api.domain.account_token.expires_at import ExpiresAt


@dataclass(frozen=True, kw_only=True)
class AccountToken(Entity):
    account_id: UUID
    fingerprint: Fingerprint
    expires_at: ExpiresAt

    # #
    # factory

    @classmethod
    @typecheck
    def new(cls, *, account_id: UUID, fingerprint: Fingerprint, expires_at: ExpiresAt) -> "AccountToken":
        account_token = cls(
            account_id=account_id,
            fingerprint=fingerprint,
            expires_at=expires_at,
            by_factory=True,
        )
        return account_token

    # #
    # query

    def is_expired(self, *, now: datetime) -> bool:
        return self.expires_at.is_past(now=now)

    def to_dict(self):
        return {
            "id": str(self.id),
            "account_id": str(self.account_id),
            "expires_at": self.expires_at.to_str(),
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }

    def to_model(self):
        return {
            "id": self.id,
            "account_id": self.account_id,
            "fingerprint": self.fingerprint.to_str(),
            "expires_at": self.expires_at.to_datetime(),
        }
