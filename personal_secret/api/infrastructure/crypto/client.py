from __future__ import annotations

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error, VerifyMismatchError

from personal_secret.api.infrastructure.common.exception import CryptoError


# #
# crypto (서버 측 — 인증 해시 + 토큰만. 시크릿/키 암복호는 클라가 함 = E2EE)

class Crypto:
    def __init__(self):
        self._password_hasher = PasswordHasher()

    # #
    # password (login_proof → login_verifier 검증)

    def hash_password(self, *, password: str) -> str:
        return self._password_hasher.hash(password)

    def verify_password(self, *, hash: str, password: str) -> bool:
        try:
            return self._password_hasher.verify(hash, password)
        except VerifyMismatchError:
            return False
        except Argon2Error as exc:
            raise CryptoError(operation="verify_password", reason=str(exc))

    # #
    # token (불투명 세션 토큰 — 원본은 발급 1회만, 저장은 fingerprint)

    def generate_token(self) -> str:
        return secrets.token_urlsafe(32)

    def hash_token(self, *, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()


# #
# Crypto

crypto = Crypto()
