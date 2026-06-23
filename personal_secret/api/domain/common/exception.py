from __future__ import annotations

from personal_secret.api.core.exception import ClientError


# #
# base

class DomainClientError(ClientError):
    ...


# #
# validation

class InvalidError(DomainClientError):
    def __init__(self, target: str = "값"):
        super().__init__(key="invalid", params={"target": target}, code=400)


class InvalidFormatError(DomainClientError):
    def __init__(self, target: str = "값"):
        super().__init__(key="invalid_format", params={"target": target}, code=400)


# #
# lookup

class NotFoundError(DomainClientError):
    def __init__(self, target: str, identifier: str):
        super().__init__(key="not_found", params={"target": target, "identifier": identifier}, code=404)


# #
# uniqueness

class AlreadyExistsError(DomainClientError):
    def __init__(self, target: str, identifier: str):
        super().__init__(key="already_exists", params={"target": target, "identifier": identifier}, code=409)


# #
# auth

class InvalidCredentialError(DomainClientError):
    def __init__(self):
        super().__init__(key="invalid_credential", params={}, code=401)


class UnauthorizedError(DomainClientError):
    def __init__(self):
        super().__init__(key="unauthorized", params={}, code=401)


class ForbiddenError(DomainClientError):
    def __init__(self, target: str = "리소스"):
        super().__init__(key="forbidden", params={"target": target}, code=403)
