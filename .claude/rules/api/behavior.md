---
paths:
  - "personal_secret/api/behavior/*.py"
  - "personal_secret/api/behavior/**/*.py"
---

# behavior

`behavior/`는 한 요청(unit of work)을 감싸는 cross-cutting **능동 정책** 레이어다 — 트랜잭션 경계(UoW)·인증·멤버십 인가·테넌트 스코프(RLS)·이벤트 디스패치가 산다. FastAPI `Depends`로 한 의존성에 조립되고, 엔드포인트는 그 의존성만 얇게 끌어쓴다.

---

## 동사(behavior) vs 명사(context)

| 결 | 무엇 | 예 |
|---|---|---|
| behavior (동사) | 작업을 감싸 *무엇을 한다* | UoW, tenant scope, event dispatch |
| context (명사) | 작업이 *그 안에서 도는* 신원 데이터 | account_id, team_id, event_group_id |

- 어원: behave = be + have → 행동 방식. CS 관용 state(명사) ↔ behavior(동사).
- 신원 DTO(`*Context`)는 behavior가 *사용/생산*하는 값이지 behavior가 아니다 — `.setup()`으로 자기를 해소하고 `context/`에 산다. behavior는 그 setup들을 순서대로 엮는 `use_postgresql_*` 의존성이다.

---

## 구조

조합(composition)과 부품(primitive)으로 가른다 — `server.py`·`worker.py`는 진입별 UoW **조합**(앱의 `bin/server.py`·`bin/worker.py`와 미러링), `context/`·`action/`은 둘이 공유하는 **부품 풀**. (단일 infra postgresql이라 infra 층 없음 — 생기면 `behavior/redis/` 식으로 옆에.)

```
behavior/
├── __init__.py     public facade — splitter + worker UoW re-export
├── server.py       HTTP 요청 UoW — Scope + 제너레이터 + session/context splitter
├── worker.py       이벤트 처리 UoW — use_postgresql_with_action (claim → scope → yield → succeed/fail)
├── context/        신원 DTO (+ .setup) — 마커 Context
│   ├── access.py   AccountContext / TeamAccessContext / OwnerAccessContext
│   └── event.py    EventGroupContext
└── action/         순수 동작 — 마커 Action
    ├── tenant.py   Tenant.set_tenant_scope   (RLS scope — server·worker 공유)
    ├── event.py    Event.dispatch_event   (NOTIFY producer — server)
    └── act.py      Act.claim / succeed / fail   (DispatchStatus 전이 — worker)
```

- **조합** (`server.py`·`worker.py`) = 부품을 진입에 맞게 얇게 조립. server는 인증·멤버십·scope·event group을, worker는 claim·scope(이벤트 팀)·succeed/fail을 엮는다. 둘 다 business는 무지 — server는 endpoint, worker는 `endpoint/internal/`이 바인딩([endpoint-internal.md](endpoint-internal.md)).
- **context/** = 신원 DTO + `.setup()`(인증·멤버십 해소). 마커 `Context`. 현재는 전부 server 전용(HTTP 인증).
- **action/** = 순수 동작(RLS·NOTIFY·dispatch 전이). 마커 `Action`. 소유가 섞인 풀 — `Tenant`(공유)·`Event`(server)·`Act`(worker). UoW만 호출 — context는 action을 직접 안 부른다.

---

## 의존성 = UoW 제너레이터

요청당 의존성 하나. 트랜잭션 세션을 열고 `Scope`를 yield하는 async 제너레이터다.

네이밍: `use_postgresql[_with_authenticated_<role>]_and_event`. 접근 레벨이 이름에 박힌다:

| 레벨 | 의존성 | 끌어오는 것 |
|---|---|---|
| 미인증 | `use_postgresql_with_event` | 세션 + event group |
| account | `use_postgresql_with_authenticated_account_and_event` | + Bearer 인증(account_id) |
| team | `use_postgresql_with_authenticated_team_and_event` | + 멤버십 + RLS 스코프 |
| owner | `use_postgresql_with_authenticated_owner_and_event` | + owner 역할 + RLS 스코프 |

제너레이터 본문 순서 (Before → yield → After):

```python
# good: 인증 → 멤버십 → 테넌트 스코프 → event group → yield → dispatch
account = await AccountContext.setup(session=session, authorization=authorization)
team    = await TeamAccessContext.setup(team_id=team_id, session=session, account=account)
await Tenant.set_tenant_scope(session=session, team_id=team_id)   # 멤버십 확인 *후* 스코프
event_group = await EventGroupContext.setup()
yield Scope(session=session, account_id=team.account_id, team_id=team.team_id, event_group_id=event_group.event_group_id)
# After (커밋 후)
await Event.dispatch_event(event_group_id=event_group.event_group_id)
```

- 멤버십 검증을 RLS 스코프보다 **먼저** — 비멤버가 요청한 `team_id`로 스코프 걸기 전에 차단.
- 미인증 라우트(register·login·salts)는 `AccountContext.setup`을 거치면 안 된다(인증 전) → `use_postgresql_with_event`.

---

## Scope + splitter — endpoint는 session·context 두 파라미터

제너레이터는 `Scope`(session + account_id + team_id + event_group_id)를 yield한다. 엔드포인트는 이걸 **splitter 두 개로 나눠 받는다 — `session`과 `context`만**. 단일 `scope` 파라미터는 패턴이 아니다.

```python
# good: session + context 두 파라미터
async def post_create(
    team_id: UUID,
    body: secret_create.Input,
    *,
    session=Depends(use_postgresql_session_with_authenticated_team_and_event),
    context=Depends(use_postgresql_context_with_authenticated_team_and_event),
) -> JSONResponse:
    created = await secret_create.create(
        session=session,
        event_group_id=context.event_group_id,
        input=body,
        team_id=team_id,
        account_id=context.account_id,
    )

# bad: 단일 scope — session/context로 가른다
async def post_create(..., *, scope=Depends(use_postgresql_with_authenticated_team_and_event)): ...
```

- splitter 쌍: `_session_`(→ `AsyncSession`) + `_context_`(→ `Scope`). 둘 다 같은 제너레이터를 `Depends` — FastAPI가 제너레이터를 캐시해 한 번만 실행, 같은 `Scope`를 공유한다.
- usecase 인자: `session=session`, `event_group_id`/`account_id`는 `context.*`에서, `team_id`는 path param.

---

## public facade — `__init__.py`

외부 소비자(endpoint)는 facade에서만 가져온다. 내부 경로로 직접 들어가지 않는다.

```python
# good: facade에서 splitter
from personal_secret.api.behavior import use_postgresql_session_with_authenticated_team_and_event

# bad: 내부 경로 직접
from personal_secret.api.behavior.server import use_postgresql_session_with_authenticated_team_and_event
```

- facade가 노출하는 공개 표면 = **splitter들** + worker UoW(`use_postgresql_with_action`). 제너레이터·`Scope`·`*Context`·`Action`은 내부 전용(facade에 안 띄운다).
- 효과: 내부 파일 재배치가 외부를 안 깬다. behavior 한정 — domain 등은 namespace 패키지로 deep import.

---

## 조립 — endpoint ↔ 레벨

| 라우트 | 레벨 | 근거 |
|---|---|---|
| auth (register·login·salts) | 미인증 | 인증 이전 |
| account 조회, team 생성 | account | team_id 없음 — 멤버십 검증 불가 |
| team 멤버 작업 (secret 전부, team key 조회) | team | 멤버면 충분 |
| team owner 작업 (멤버 초대·삭제, 키 로테이션) | owner | owner 역할 필요 |

- 레벨은 의존성 이름이 곧 강제 — endpoint는 라우트에 맞는 splitter 쌍 하나만 고른다.
- team/owner 제너레이터가 멤버십·RLS를 한 번에 끌어온다 — RLS만 거는 별도 의존성을 두지 않는다(비멤버 노출 위험).
