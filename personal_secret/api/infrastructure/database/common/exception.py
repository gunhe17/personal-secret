from __future__ import annotations

from personal_secret.api.infrastructure.common.exception import InfrastructureClientError, InfrastructureDevelopError


# #
# develop

class DatabaseError(InfrastructureDevelopError):
    def __init__(self, operation: str, reason: str):
        super().__init__(message=f"DB 실패 (작업: {operation}, 원인: {reason})", code=500)


# #
# client

class UniqueViolationError(InfrastructureClientError):
    def __init__(self):
        super().__init__(message="이미 존재합니다", code=409)
