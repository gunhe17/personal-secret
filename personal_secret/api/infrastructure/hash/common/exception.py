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
        super().__init__(message=f"hash verify 실패 (원인: {reason})", code=500)


class UnsupportedError(HashError):
    def __init__(self, operation: str):
        super().__init__(message=f"hash {operation} 미지원", code=500)
