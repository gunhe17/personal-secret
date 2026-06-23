from __future__ import annotations

from enum import StrEnum


# #
# locale

class Locale(StrEnum):
    KO = "ko"
    EN = "en"


# #
# catalog

_CATALOG = {
    "invalid": {
        Locale.KO: "{target} 타입이 올바르지 않습니다",
        Locale.EN: "{target} has an invalid type",
    },
    "invalid_format": {
        Locale.KO: "{target} 형식이 올바르지 않습니다",
        Locale.EN: "{target} has an invalid format",
    },
    "not_found": {
        Locale.KO: "{target} 찾을 수 없습니다 (식별자: {identifier})",
        Locale.EN: "{target} not found (identifier: {identifier})",
    },
    "already_exists": {
        Locale.KO: "{target} 이미 존재합니다 (식별자: {identifier})",
        Locale.EN: "{target} already exists (identifier: {identifier})",
    },
    "invalid_credential": {
        Locale.KO: "이메일 또는 비밀번호가 올바르지 않습니다",
        Locale.EN: "Invalid email or password",
    },
    "unauthorized": {
        Locale.KO: "인증이 필요합니다",
        Locale.EN: "Authentication required",
    },
    "forbidden": {
        Locale.KO: "{target}에 대한 권한이 없습니다",
        Locale.EN: "No permission for {target}",
    },
    "unique_violation": {
        Locale.KO: "이미 존재합니다",
        Locale.EN: "Already exists",
    },
    "database_error": {
        Locale.KO: "DB 실패 (작업: {operation}, 원인: {reason})",
        Locale.EN: "DB failed (operation: {operation}, reason: {reason})",
    },
    "hash_verify_failed": {
        Locale.KO: "hash verify 실패 (원인: {reason})",
        Locale.EN: "hash verify failed (reason: {reason})",
    },
    "hash_unsupported": {
        Locale.KO: "hash {operation} 미지원",
        Locale.EN: "hash {operation} not supported",
    },
    "no_work_registered": {
        Locale.KO: "등록된 work 없음 (식별자: {name})",
        Locale.EN: "no work registered (identifier: {name})",
    },
    "work_failed": {
        Locale.KO: "work 처리 실패 (작업: {channel}, 원인: {reason})",
        Locale.EN: "work processing failed (operation: {channel}, reason: {reason})",
    },
    "notification_error": {
        Locale.KO: "알림 발송 실패 (원인: {reason})",
        Locale.EN: "notification send failed (reason: {reason})",
    },
    "listen_error": {
        Locale.KO: "LISTEN 실패 (작업: {operation}, 원인: {reason})",
        Locale.EN: "LISTEN failed (operation: {operation}, reason: {reason})",
    },
}


# #
# render

DEFAULT = Locale.KO

def render(*, key: str, params: dict, locale: Locale) -> str:
    templates = _CATALOG[key]
    template = templates.get(locale) or templates[DEFAULT]
    return template.format(**params)
