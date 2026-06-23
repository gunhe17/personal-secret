from __future__ import annotations

from personal_secret.api.core.exception import ClientError


# #
# base

class BehaviorClientError(ClientError):
    ...


# #
# auth

class UnauthorizedError(BehaviorClientError):
    def __init__(self):
        super().__init__(key="unauthorized", params={}, code=401)


class ForbiddenError(BehaviorClientError):
    def __init__(self, target: str = "리소스"):
        super().__init__(key="forbidden", params={"target": target}, code=403)
