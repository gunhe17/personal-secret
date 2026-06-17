from __future__ import annotations

from personal_secret.api.core.exception import ClientError, DevelopError


# #
# base

class InfrastructureDevelopError(DevelopError):
    ...


class InfrastructureClientError(ClientError):
    ...
