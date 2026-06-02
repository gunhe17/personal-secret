from __future__ import annotations

from datetime import datetime, timedelta, timezone

from personal_secret.api.config import CryptoConfig
from personal_secret.api.config import get_crypto_config

from personal_secret.api.infrastructure.crypto.client import crypto
from personal_secret.api.infrastructure.common.exception import LockedError


# #
# session

class SessionCache:
    def __init__(self, *, config: CryptoConfig):
        self._config = config
        self._dek: bytes | None = None
        self._touched_at: datetime | None = None

    def unlock(self, *, dek: bytes) -> None:
        self._dek = dek
        self._touched_at = datetime.now(timezone.utc)

    def get(self) -> bytes | None:
        if self._dek is None or self._touched_at is None:
            return None

        # sliding ttl
        ttl = timedelta(seconds=self._config.SESSION_TTL_SEC)
        if datetime.now(timezone.utc) - self._touched_at > ttl:
            self.lock()
            return None

        self._touched_at = datetime.now(timezone.utc)
        return self._dek

    def is_unlocked(self) -> bool:
        unlocked = self.get() is not None
        return unlocked

    def lock(self) -> None:
        self._dek = None
        self._touched_at = None

    # #
    # crypto (세션 DEK로 암·복호화 — 잠겨있으면 LockedError)

    def encrypt(self, *, plaintext: bytes) -> bytes:
        dek = self.get()
        if dek is None:
            raise LockedError()
        return crypto.encrypt(key=dek, plaintext=plaintext)

    def decrypt(self, *, data: bytes) -> bytes:
        dek = self.get()
        if dek is None:
            raise LockedError()
        return crypto.decrypt(key=dek, data=data)


# #
# SessionCache

session_cache = SessionCache(config=get_crypto_config())
