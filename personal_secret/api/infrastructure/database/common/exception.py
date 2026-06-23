from __future__ import annotations

from personal_secret.api.infrastructure.common.exception import InfrastructureClientError, InfrastructureDevelopError


# #
# develop

class DatabaseError(InfrastructureDevelopError):
    def __init__(self, operation: str, reason: str):
        super().__init__(key="database_error", params={"operation": operation, "reason": reason}, code=500)


class ListenError(InfrastructureDevelopError):
    def __init__(self, operation: str, reason: str):
        super().__init__(key="listen_error", params={"operation": operation, "reason": reason}, code=500)


# #
# client

class UniqueViolationError(InfrastructureClientError):
    def __init__(self):
        super().__init__(key="unique_violation", params={}, code=409)
