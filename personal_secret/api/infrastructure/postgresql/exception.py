from __future__ import annotations

from personal_secret.api.infrastructure.common.exception import InfrastructureClientError


# #
# typed (unique 사전검사가 던지는 infra 예외 — 도메인 repo가 잡아 의미 부여)

class UniqueViolationError(InfrastructureClientError):
    def __init__(self, unique_key: str | None = None):
        self.unique_key = unique_key   # 위반 컬럼 (구조화 메타 — 컬럼은 표준 라벨이 없어 메시지엔 미포함)
        super().__init__(message="이미 존재합니다", code=409)
