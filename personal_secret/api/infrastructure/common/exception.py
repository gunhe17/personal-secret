from __future__ import annotations

from personal_secret.api.core.exception import ClientError, DevelopError


# #
# base

class InfrastructureError(DevelopError):
    ...


# #
# specific

class DatabaseError(InfrastructureError):
    def __init__(self, operation: str, reason: str):
        super().__init__(
            message=f"\n\t 데이터베이스 오류 ({operation}): {reason}",
            code=500,
        )


class CryptoError(InfrastructureError):
    def __init__(self, operation: str, reason: str):
        super().__init__(
            message=f"\n\t 암호화 오류 ({operation}): {reason}",
            code=500,
        )


# #
# locked

class LockedError(ClientError):
    def __init__(self):
        super().__init__(
            message="세션이 잠겨 있습니다. (unlock 먼저 실행)",
            code=423,
        )
