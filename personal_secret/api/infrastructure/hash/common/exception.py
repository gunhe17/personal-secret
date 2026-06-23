from __future__ import annotations

from personal_secret.api.infrastructure.common.exception import InfrastructureDevelopError


# #
# base

class HashError(InfrastructureDevelopError):
    ...


# #
# develop

class VerifyError(HashError):
    def __init__(self, reason: str):
        super().__init__(key="hash_verify_failed", params={"reason": reason}, code=500)


class UnsupportedError(HashError):
    def __init__(self, operation: str):
        super().__init__(key="hash_unsupported", params={"operation": operation}, code=500)
