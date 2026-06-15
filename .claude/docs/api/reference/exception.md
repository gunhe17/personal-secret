# 예외 패턴

전 레이어 예외의 **단일 권위** — 루트(`core/exception.py`) + 레이어별 `common/exception.py` + dialect typed 예외 + 핸들러. 모든 예외는 `ClientError`(4xx)/`DevelopError`(5xx)로 귀결한다 — **[INV-4]**.

루트: [api.md](../api.md) · 핸들러 등록: [server.md](server.md)

---

## 이 문서

| 섹션 | 핵심 규칙 |
|------|----------|
| **구조** | `core/exception.py` 루트(2분류) → 레이어 `common/exception.py` 구체 예외 — **[INV-4]** |
| **메시지 규약** | head + `message` + `path` 3단, base가 에러명·범주·위치 자동 조립 |
| **4xx vs 5xx** | `ClientError` 사용자 노출·정중체 / `DevelopError` prod 마스킹·terse 진단 |
| **핸들러** | `client()`(4xx) + `internal()`(catch-all 5xx) 2개로 완결, MRO 자동 분기 |

---

## 구조 — [INV-4]

예외는 **레이어별 `common/exception.py`에 모으고, 모두 `ClientError`/`DevelopError`를 (직·간접) 상속**한다.

```
core/exception.py                          ← 루트 전용, 직접 raise 안 함
  ApplicationError(Exception)        msg·code + __trace_back__
  ├─ ClientError                     4xx · 클라이언트 책임
  └─ DevelopError                    5xx · 서버 책임

domain/common/exception.py
  DomainClientError(ClientError)           레이어 베이스 (domain은 4xx만)
  ├─ InvalidError / InvalidFormatError   400
  ├─ NotFoundError                       404
  └─ AlreadyExistsError                  409

infrastructure/common/exception.py
  InfrastructureDevelopError(DevelopError) 레이어 베이스 (5xx)
  └─ DatabaseError / CryptoError         500
  InfrastructureClientError(ClientError)   레이어 베이스 (4xx)
  └─ LockedError                         423

infrastructure/postgresql/exception.py   (dialect 고유 typed 예외)
  UniqueViolationError(InfrastructureClientError)  409 · _ensure_unique 사전검사
```

### 원칙

- **레이어 공통 예외는 `common/exception.py` 하나에** — 서브모듈(`crypto/` 등)에 일반 예외 파일 두지 않음. **단 dialect/어댑터 고유 typed 예외**(`postgresql/exception.py`의 `UniqueViolationError`)는 그 어댑터 옆에
- **`core/exception.py`는 루트 전용** — `ApplicationError` + `ClientError`/`DevelopError`만. 구체 예외(`message`/`code` 보유) 금지
- **레이어가 내는 각 HTTP 카테고리마다 레이어 베이스** — 베이스명 `{Layer}{Category}Error`. domain은 4xx만이라 `DomainClientError` 하나, infra는 `InfrastructureClientError`(423) + `InfrastructureDevelopError`(500) 둘. **모든 구체 예외는 레이어 베이스 경유** — 직접 `ClientError`/`DevelopError` 상속 우회 없음
- **미처리 예외는 `internal()` catch-all** — 단 raw 오류는 경계에서 typed 변환: DB는 `transactional_session`에서 `SQLAlchemyError → DatabaseError`, crypto는 `crypto/client.py`에서 `Exception → CryptoError`
- 구체 예외만 `message`/`code` 채움 — 베이스(`...`)는 분류용 마디
- **core 내부 가드(`by_factory`/`typecheck`)는 새 예외 없이 `DevelopError`를 직접 raise** — 구체 예외는 레이어 `common`에만

---

## 메시지 규약 — head + message + path 3단

모든 예외 메시지는 base(`ApplicationError.__init__`)가 자동 조립. 구체 예외는 description만 넘긴다:

```
{ErrorName} - {category} ({code})
	 message: {description}
	 path: {repo-relative-path}:{line}
```

- **head**: `type(self).__name__` + `_category()`(`ClientError`/`DevelopError`) + `code`. (core 가드처럼 `DevelopError` 직접 raise하면 `DevelopError - DevelopError (500)` — 의도된 표기)
- **`message`**: description 한 줄. 형식 `{주어} {서술} (라벨: 값[, ...])` — 디테일은 전부 괄호 + 한국어 `라벨: 값` 쌍. 표준 라벨: `식별자`/`원인`/`실제`/`작업`/`조치`/`허용`
- **`path` (`_origin`)**: 스택에서 `exception.py` 프레임 스킵하고 처음 만나는 호출자 프레임 → 실제 raise한 도메인/usecase 위치

### 4xx vs 5xx 스타일

| 분류 | 노출 | 문체 | 내용 |
|------|------|------|------|
| `ClientError` (4xx) | prod에서도 사용자 노출 | 정중 평서체 `~습니다`, 힌트 `(조치: unlock)` | 어휘 통일 — 타입 `타입이 올바르지 않습니다`, 형식 `형식이 올바르지 않습니다`, 미존재 `찾을 수 없습니다 (식별자: X)`, 중복 `이미 존재합니다 (식별자: X)` |
| `DevelopError` (5xx) | prod 마스킹(`error_id`만), dev/로그만 | terse 진단(정중체·마침표 없음) | 실제 타입/값/operation/reason OK — `{param} {expected} 필요 (실제: {actual})`, `DB 실패 (작업: {op}, 원인: {reason})` |

```
# ClientError (4xx) — 사용자 노출, 정중체
NotFoundError - ClientError (404)
	 message: Secret 찾을 수 없습니다 (식별자: github-token)
	 path: personal_secret/api/domain/secret/secret_repository.py:128

# DevelopError (5xx) — prod 마스킹, dev/로그, terse
DevelopError - DevelopError (500)
	 message: kind <class 'Kind'> 필요 (실제: str)
	 path: personal_secret/api/core/validate.py:24
```

---

## 핸들러 — 2개로 4xx/5xx 완결

핸들러 *팩토리*는 `server/exception.py`, *등록*은 `bin/server.py`([server.md](server.md)). Starlette가 `type(exc).__mro__`로 가장 구체적인 핸들러 선택.

- `client()` → `ClientError` 등록. `exc.code`(400~423) 그대로 응답, dev에서만 traceback 첨부
- `internal()` → **`Exception` 등록(catch-all)**. `ClientError` 외 **모든 예외**(`DevelopError`·raw DB 오류·`RuntimeError`)를 500으로. 항상 로그(`error_id` + traceback), dev에서만 상세 노출, 그 외 마스킹 + `error_id`만

---

## 안티패턴

- ❌ 서브모듈에 레이어 공통 예외 파일(`crypto/exception.py`) → `common/exception.py`에 집약(dialect 고유는 예외)
- ❌ `core/exception.py`에 구체 예외 추가 → 루트엔 `ApplicationError` + 2분류만
- ❌ 구체 예외가 `ClientError`/`DevelopError`를 직접 상속 → 레이어 베이스(`{Layer}{Category}Error`) 경유
- ❌ raw DB/crypto 오류를 그대로 전파 → 경계에서 typed 변환(`DatabaseError`/`CryptoError`)
- ❌ 예외 핸들러를 카테고리별 N개 등록 → `client()`/`internal()` 2개로 충분(MRO 분기)
