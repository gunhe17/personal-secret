from __future__ import annotations

import hashlib

from personal_secret.api.infrastructure.hash.common.client import Hash
from personal_secret.api.infrastructure.hash.common.exception import UnsupportedError


# #
# sha256

class Sha256(Hash):
    def hash(self, *, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def verify(self, *, hash: str, value: str) -> bool:
        raise UnsupportedError(operation="verify")


# #
# client

sha256 = Sha256()
