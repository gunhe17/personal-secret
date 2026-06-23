from __future__ import annotations

from personal_secret.api.infrastructure.common.exception import InfrastructureDevelopError


# #
# develop

class NotificationError(InfrastructureDevelopError):
    def __init__(self, reason: str):
        super().__init__(key="notification_error", params={"reason": reason}, code=500)
