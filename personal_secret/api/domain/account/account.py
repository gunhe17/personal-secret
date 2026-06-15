from __future__ import annotations

from dataclasses import dataclass

from personal_secret.api.core.entity import Entity
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.account.email import Email
from personal_secret.api.domain.account.personal_lock import PersonalLock
from personal_secret.api.domain.account.personal_locked_key import PersonalLockedKey
from personal_secret.api.domain.account.personal_unlock_salt import PersonalUnlockSalt
from personal_secret.api.domain.account.login_salt import LoginSalt
from personal_secret.api.domain.account.login_verifier import LoginVerifier


@dataclass(frozen=True, kw_only=True)
class Account(Entity):
    email: Email
    personal_lock: PersonalLock
    personal_locked_key: PersonalLockedKey
    personal_unlock_salt: PersonalUnlockSalt
    login_salt: LoginSalt
    login_verifier: LoginVerifier

    # #
    # factory

    @classmethod
    @typecheck
    def new(
        cls,
        *,
        email: Email,
        personal_lock: PersonalLock,
        personal_locked_key: PersonalLockedKey,
        personal_unlock_salt: PersonalUnlockSalt,
        login_salt: LoginSalt,
        login_verifier: LoginVerifier,
    ) -> "Account":
        account = cls(
            email=email,
            personal_lock=personal_lock,
            personal_locked_key=personal_locked_key,
            personal_unlock_salt=personal_unlock_salt,
            login_salt=login_salt,
            login_verifier=login_verifier,
            by_factory=True,
        )
        return account

    # #
    # query

    def to_dict(self):
        return {
            "id": str(self.id),
            "email": self.email.to_str(),
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }

    def to_keys(self):
        return {
            "personal_lock": self.personal_lock.to_str(),
            "personal_locked_key": self.personal_locked_key.to_str(),
            "personal_unlock_salt": self.personal_unlock_salt.to_str(),
            "login_salt": self.login_salt.to_str(),
        }

    def to_model(self):
        return {
            "id": self.id,
            "email": self.email.to_str(),
            "personal_lock": self.personal_lock.to_str(),
            "personal_locked_key": self.personal_locked_key.to_str(),
            "personal_unlock_salt": self.personal_unlock_salt.to_str(),
            "login_salt": self.login_salt.to_str(),
            "login_verifier": self.login_verifier.to_str(),
        }
