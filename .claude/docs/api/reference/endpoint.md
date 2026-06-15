# endpoint 패턴

FastAPI route handlers. usecase 호출 + HTTP 응답 변환. **비즈니스 로직 0.** `endpoint/{aggregate}.py`에 산다.

루트: [api.md](../api.md) · 흐름: [usecase-flow.md](usecase-flow.md) · 등록: [server.md](server.md)

---

## 이 문서

| 섹션 | 핵심 규칙 |
|------|----------|
| **책임** | usecase 호출 + HTTP 응답 변환만. 비즈니스 로직 0 |
| **핸들러 네이밍** | HTTP 메서드 접두 — `post_create` / `get_reveal` |
| **등록** | endpoint가 아니라 합성 루트 `bin/server.py`에서 ([server.md](server.md)) |

---

## 책임 + 패턴

aggregate별 route handler 모음(`secret.py`). usecase 함수를 호출하고 결과(usecase가 조립한 인라인 dict)를 그대로 HTTP 응답으로 변환만 한다 — **[INV-8]**.

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from personal_secret.api.infrastructure.postgresql.session import transactional_session_helper
from personal_secret.api.usecase.secret import create

# #
# command

async def post_create(
    body: create.Input,
    session: AsyncSession = Depends(transactional_session_helper),
) -> JSONResponse:
    created = await create.create(session=session, input=body)
    return JSONResponse(status_code=200, content=created)
```

- **핸들러는 HTTP 메서드 접두** — `post_create`/`get_reveal`. 라우트 메서드를 이름에서 바로 읽는다(usecase 함수명 `create`/`reveal`과 구분)
- session은 `Depends(transactional_session_helper)`로 주입받아 usecase에 넘긴다 (**[INV-5]**, [usecase-flow.md](usecase-flow.md))
- 검증/도메인 조작/transaction 조정은 전부 아래 레이어가 — endpoint는 얇게
- 예외는 직접 처리하지 않는다 — `ClientError`/`DevelopError`가 핸들러로 자동 분기 (**[INV-4]**, [exception.md](exception.md))
- **등록은 endpoint가 아니라 `bin/server.py`(합성 루트)에서** — endpoint는 핸들러만 정의([server.md](server.md))

---

## 안티패턴

- ❌ endpoint에서 입력 검증·도메인 조작·transaction 조정 → 아래 레이어로, endpoint는 얇게
- ❌ 예외를 endpoint에서 try/except → 핸들러 자동 분기 (**[INV-4]**)
- ❌ usecase 결과를 재가공/래핑 → 인라인 dict 그대로 응답 (**[INV-8]**)
- ❌ endpoint가 자기를 라우터에 등록 → `bin/server.py` 단일 출처 ([server.md](server.md))
