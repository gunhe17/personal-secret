from __future__ import annotations

from personal_secret.api.core.exception import ClientError


# #
# base

class DomainError(ClientError):
    ...


# #
# validation

class InvalidError(DomainError):
    def __init__(self, target: str = "값"):
        super().__init__(
            message=f"{target}: 타입이 유효하지 않습니다.",
            code=400,
        )


class InvalidFormatError(DomainError):
    def __init__(self, target: str = "값"):
        super().__init__(
            message=f"{target}: 형식이 유효하지 않습니다.",
            code=400,
        )


# #
# lookup

class NotFoundError(DomainError):
    def __init__(self, target: str, identifier: str):
        super().__init__(
            message=f"\n\t {target}, 찾을 수 없습니다. (식별자: {identifier})",
            code=404,
        )


# #
# uniqueness

class AlreadyExistsError(DomainError):
    def __init__(self, target: str, identifier: str):
        super().__init__(
            message=f"\n\t {target}, 이미 존재합니다. (식별자: {identifier})",
            code=409,
        )


# #
# vault lifecycle

class NotInitializedError(DomainError):
    def __init__(self):
        super().__init__(
            message="볼트가 아직 초기화되지 않았습니다. (init 먼저 실행)",
            code=409,
        )


class AlreadyInitializedError(DomainError):
    def __init__(self):
        super().__init__(
            message="볼트가 이미 초기화되어 있습니다.",
            code=409,
        )


class InvalidMasterPasswordError(DomainError):
    def __init__(self):
        super().__init__(
            message="마스터 비밀번호가 올바르지 않습니다.",
            code=401,
        )
