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
        super().__init__(message=f"{target} 타입이 올바르지 않습니다", code=400)


class InvalidFormatError(DomainClientError):
    def __init__(self, target: str = "값"):
        super().__init__(message=f"{target} 형식이 올바르지 않습니다", code=400)


# #
# lookup

class NotFoundError(DomainClientError):
    def __init__(self, target: str, identifier: str):
        super().__init__(message=f"{target} 찾을 수 없습니다 (식별자: {identifier})", code=404)


# #
# uniqueness

class AlreadyExistsError(DomainClientError):
    def __init__(self, target: str, identifier: str):
        super().__init__(message=f"{target} 이미 존재합니다 (식별자: {identifier})", code=409)


# #
# auth

class InvalidCredentialError(DomainClientError):
    def __init__(self):
        super().__init__(message="이메일 또는 비밀번호가 올바르지 않습니다", code=401)


class UnauthorizedError(DomainClientError):
    def __init__(self):
        super().__init__(message="인증이 필요합니다", code=401)


class ForbiddenError(DomainClientError):
    def __init__(self, target: str = "리소스"):
        super().__init__(message=f"{target}에 대한 권한이 없습니다", code=403)
