from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error, VerifyMismatchError

from personal_secret.api.infrastructure.hash.common.client import Hash
from personal_secret.api.infrastructure.hash.common.exception import VerifyError


# #
# argon2

class Argon2(Hash):
    def __init__(self):
        self._hasher = PasswordHasher()

    def hash(self, *, value: str) -> str:
        return self._hasher.hash(value)

    def verify(self, *, hash: str, value: str) -> bool:
        try:
            return self._hasher.verify(hash, value)
        
        except VerifyMismatchError:
            return False
        
        except Argon2Error as exc:
            raise VerifyError(reason=str(exc))


# #
# client

argon2 = Argon2()
