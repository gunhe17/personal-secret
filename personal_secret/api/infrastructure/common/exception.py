from __future__ import annotations

from personal_secret.api.core.exception import ClientError, DevelopError


# #
# base

class InfrastructureDevelopError(DevelopError):   # 5xx — 서버 책임
    ...


class InfrastructureClientError(ClientError):     # 4xx — 클라이언트 책임
    ...


# #
# develop

class DatabaseError(InfrastructureDevelopError):
    def __init__(self, operation: str, reason: str):
        super().__init__(message=f"DB 실패 (작업: {operation}, 원인: {reason})", code=500)


class CryptoError(InfrastructureDevelopError):
    def __init__(self, operation: str, reason: str):
        super().__init__(message=f"crypto 실패 (작업: {operation}, 원인: {reason})", code=500)
