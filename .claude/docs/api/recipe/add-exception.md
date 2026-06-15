# Recipe: 예외 추가

새 구체 예외 추가 또는 이동. 규칙 본문은 [reference/exception.md](../reference/exception.md).

## 절차

1. **카테고리 판정** — 클라이언트 책임(4xx) → `ClientError` 계열 / 서버 책임(5xx) → `DevelopError` 계열
2. **파일 선택** — 레이어 `common/exception.py` (domain → `domain/common/`, infra → `infrastructure/common/`). dialect 고유 typed 예외(PostgreSQL unique 등)만 `infrastructure/postgresql/exception.py`
   - ❌ `core/exception.py`엔 추가 금지(루트 전용) — **[INV-4]**
   - ❌ 서브모듈(`crypto/exception.py`)에 레이어 공통 예외 금지
3. **상속** — 레이어 베이스(`{Layer}{Category}Error`) 경유. 없으면 베이스부터 추가(`ClientError`/`DevelopError`를 직접 상속하는 우회 금지)
4. **`message`/`code` 채움** — description만 넘기면 base가 head+path 자동 조립. 형식 `{주어} {서술} (라벨: 값)`, 표준 라벨 `식별자`/`원인`/`실제`/`작업`/`조치`/`허용`
   - 4xx: 정중체 `~습니다`, 사용자 노출 / 5xx: terse 진단, prod 마스킹
5. **raise 위치** — 도메인 의미 변환은 도메인이(예: `UniqueViolationError` → `AlreadyExistsError`). raw DB/crypto 오류는 경계에서 typed 변환
6. **핸들러는 손대지 않는다** — `client()`/`internal()` 2개가 MRO로 자동 분기([reference/server.md](../reference/server.md))

## 체크

- [ ] 레이어 베이스 경유했나 (직접 `ClientError`/`DevelopError` 상속 금지) — **[INV-4]**
- [ ] `core/exception.py` 안 건드렸나
- [ ] raw 오류를 그대로 전파 안 했나 → typed 변환
