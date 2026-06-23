---
paths:
  - "personal_secret/api/bin/worker.py"
  - "personal_secret/api/worker/**"
---

# worker + bin 패턴 (합성 루트)

프레임워크 프리미티브(`worker/`) + 합성 루트(`bin/worker.py`). NOTIFY 구독 프로세스를 조립한다 — channel↔handler 등록 + 동시성·시그널 런타임. 비즈니스 로직 0, 도메인 의존 0. HTTP 쪽 `server/`([server.md](server.md))의 짝.

루트: [api/CLAUDE.md](../../../personal_secret/api/CLAUDE.md) · 핸들러: [endpoint-internal.md](endpoint-internal.md) · UoW: [behavior.md](behavior.md) · dispatch: [domain-event.md](domain-event.md)

---

## 이 문서

| 섹션 | 핵심 규칙 |
|------|----------|
| **프레임워크 프리미티브** | `Worker`(등록 큐 + `run()`) + `Work`(channel/handler 어댑터) + `Pool`/`Lifecycle`(런타임) |
| **합성 루트** | `bin/worker.py`에서 `worker.work(Work(...))` 등록 + `asyncio.run(worker.run())` |
| **도메인 무지** | `worker/`는 `Handler = Callable[[str], Awaitable]`만 안다 — business는 internal endpoint([endpoint-internal.md](endpoint-internal.md)) |

---

## 프레임워크 프리미티브 (`worker/`)

도메인을 모르는 순수 런타임 — raw NOTIFY payload(`str`)를 받아 `Callable` handler에 넘긴다.

| 파일 | 내용 |
|------|------|
| `worker/worker.py` | `Worker` — 등록 큐(`work()`) + `run()`(연결→각 work 등록→시그널 대기→연결 close + pool drain). `personal_secret_worker()` 팩토리 |
| `worker/work.py` | `Work` — `channel`/`handler` 래퍼, `register(connection, pool)`로 asyncpg listener를 단다(콜백 = `pool.submit(handler(payload))`). handler 예외는 `WorkFailedError`로 격리 |
| `worker/pool.py` | `Pool` — `asyncio.Semaphore` 동시성 상한 + in-flight 태스크 추적 + `wait()` drain(graceful shutdown 시 잔여 완료 대기) |
| `worker/lifecycle.py` | `Lifecycle` — `SIGTERM`/`SIGINT` → `asyncio.Event`, `run()`이 그 신호까지 블록 |

`Work`는 `server/`의 래퍼와 같은 결 — 생성자에 설정(`channel`/`handler`) 받고 `register(...)` 하나. `Server.app()`이 `register(app)`을 순회하듯 `Worker.run()`이 `register(connection, pool)`을 순회한다(`app` ↔ `(connection, pool)`).

---

## 합성 루트 — `bin/worker.py`

work 등록이 일어나는 단 한 곳. internal endpoint 핸들러를 `Work`로 감싸 `worker.work(...)`.

```python
from personal_secret.api.worker.worker import personal_secret_worker
from personal_secret.api.worker.work import Work
from personal_secret.api.endpoint.internal import event      # 모듈 namespace import

# #
# worker
worker = personal_secret_worker()

# work
worker.work(
    Work(channel="event_group", handler=event.on_event_group)
)

# #
# run
if __name__ == "__main__":
    asyncio.run(worker.run())
```

- handler는 모듈 namespace로 import (`from ...endpoint.internal import event` → `event.on_event_group`) — registry 규칙([conventions.md](../shared/conventions.md) "라우터/registry")
- handler 이름은 트리거(채널) 접두 `on_{channel}` — [endpoint-internal.md](endpoint-internal.md)
- `# worker` / `# run` 섹션 마커로 구획, `run()`은 모듈 끝 `__main__`에서
- 조립은 전부 `bin/worker.py`에 — worker/·endpoint는 자기를 등록하지 않는다(등록의 단일 출처). `server.router(Router(...))` ↔ `worker.work(Work(...))` 대칭([server.md](server.md))

---

## 책임 경계 — worker는 디스패처, business는 위임

`worker/`는 "NOTIFY를 받아 handler를 동시성 제어 하에 돌린다"만. claim/dispatch/reaction은 안 만진다.

- payload 파싱 + UoW 진입 + business 호출 → internal endpoint(`endpoint/internal/`, [endpoint-internal.md](endpoint-internal.md))
- claim→business→succeed/fail UoW → `behavior/worker.py`([behavior.md](behavior.md))
- 라우팅·reaction → usecase(`event_dispatch`, [domain-event.md](domain-event.md))
- handler 예외는 `Work`가 `WorkFailedError`로 잡아 격리 — 한 작업 실패가 listener를 안 죽인다(현재 `print`, 감사 logger는 별도)

---

## 안티패턴

- `worker/`가 domain/usecase를 import → 런타임 프리미티브는 도메인 무지(`Handler` Callable만) — **[INV-1]**, `server/`와 동일
- business/claim/dispatch 로직을 `worker/`에 인라인 → internal endpoint + `behavior` UoW + usecase로
- 동시성·시그널 처리를 `bin/worker.py`에 인라인 → `Pool`/`Lifecycle` 프리미티브에, bin은 등록 + `run()` 호출만
- handler/Work가 자기를 등록 → `bin/worker.py` 단일 출처(`server/`의 endpoint 자가등록 금지와 동일)
