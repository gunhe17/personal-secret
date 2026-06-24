---
paths:
  - "personal_secret/api/**/*_event.py"
  - "personal_secret/api/domain/event/**"
  - "personal_secret/api/core/event.py"
---

# Domain Event 패턴

도메인 행위가 낳는 이벤트를 세 군데로 분업 — atomic(domain·순수) / 저장(`EventRepository.emit`·두 aggregate) / 조정(usecase). atomic은 `emit`을 직접 호출하지 않는다. 저장은 루트 `Event`(`domain/event/event/` — dispatch 봉투: name/status + reaction 완료 ledger(`attempts` JSON)/claimed_at 등, payload 없음)와 자식 `AtomicEvent`(`domain/event/atomic_event/`, `atomic_events` 테이블 — "어느 엔티티가 어떻게 변했나" 엔티티 인덱스 + 자기 소비 스냅샷 `payload`, append-only 성공 접근 로그, 도메인 변경과 같은 트랜잭션에 원자적으로 기록)로 나뉜다. 따라서 실패/거부는 `AtomicEvent`에 담기지 않는다(repo 오류·`raise`는 롤백되어 atomic도 사라짐). 실패/시도 감사(인증 실패·권한 거부)는 트랜잭션 밖 별도 logger 채널의 몫 — 이 테이블에 섞지 않는다.

스키마 문법은 주어-동사-목적어: `actor_id`(주어)가 `actor_team_id`에서 `act`(동사)를 `act_entity_name`/`act_entity_id`(목적어)에 했고, 한 액션은 `event_id`로 어느 `Event`에 속하는지 묶이며 그 `Event`의 `name`이 묶음 이름(= usecase 식별, 예 `"secret_create"`)이다. read(조회)도 `act="read"`로 기록되는 성공 접근 신호다.

`Event.id`(어느 실행 — 런타임 uuid, instance)와 `Event.name`(어느 usecase — 정적 라벨, type)은 한 entity에 같이 살되 출처가 다르다: `id`는 런타임에만 알 수 있어 요청당 1개 생성 후 스레딩(behavior `Scope`), `name`은 usecase마다 고정값이라 묶음을 조정하는 usecase가 emit 호출에서 자기 이름을 직접 공급한다(= 단일 출처, CLI 경로도 자동 커버). `Event` 1건이 `AtomicEvent` N건을 묶는 dispatch 단위라 claim 상태·reaction 완료 ledger(`attempts`) 같은 운영 상태는 `Event`에만 산다. payload는 각 `AtomicEvent`가 자기 몫을 들고, dispatch가 atomic마다 reaction을 한 번씩 실행한다(N fan-out).

루트: [api/CLAUDE.md](../../../personal_secret/api/CLAUDE.md) · entity: [entity.md](entity.md) · repo: [repository.md](repository.md) · 흐름: [usecase-flow.md](usecase-flow.md)

---

## 이 문서

| 섹션 | 핵심 규칙 |
|------|----------|
| atomic (domain) | core `Event`(`core/event.py`, domain aggregate `Event`와 별개) 상속 순수 atomic, IO/async·타 aggregate 의존 0 — [INV-7]. "무엇에 무슨 행위"(목적어+동사) + 자기 aggregate 평문 `payload()`만 안다 |
| 저장 — 루트 | `EventRepository.emit`이 묶음(occurrence) 1건을 idempotent upsert (name + dispatch 상태만, payload 없음) |
| 저장 — 자식 | `emit` 내부에서 atomic → `AtomicEvent`(엔티티 인덱스 + 자기 `payload()`) 변환 + actor 스탬프 후 `AtomicEventModel`로 직접 영속(자식 전용 repository 없음) |
| 조정 (usecase) | 도메인 변경 + atomic + `emit`(같은 session, actor 전달) + `Output(data, event)` 응답 — [INV-8] |
| dispatch (worker) | `Event.name`으로 라우팅 → 그 Event의 atomic들을 순회, atomic마다 reaction `Input.from_event(atomic)` 실행 (1 atomic = 1 reaction, N fan-out) |
| vocabulary | `{Aggregate}EventKind` 값 = `act` 표기(`"created"`/`"read"`), `Act._allowed_list` 미러링. 대상은 `act_entity_name`(`"secret"`)으로 분리 |

---

## atomic — 순수 (domain) — [INV-7]

`{aggregate}_event.py`에 산다. `core/event.py`의 `Event`(`_id` + `id()`만 가진 frozen atomic base) 상속, IO·async·다른 aggregate 의존 0. 모든 write/read aggregate가 자기 atomic을 가진다. atomic은 목적어+동사 + 자기 aggregate 평문만 — 누가(`actor_id`)·어느 팀(`actor_team_id`)·묶음(`event_id`/묶음 이름)은 요청·usecase 맥락이라 `emit`이 채운다.

```python
# domain/secret/secret_event.py
@dataclass(frozen=True, kw_only=True)
class SecretEvent(Event):
    _kind: SecretEventKind         # Enum, 값은 act "created"/"read" (act_entity_name 은 atomic이 상수로)
    secret: Secret

    # #
    # factory  (@classmethod @typecheck, sync)

    @classmethod
    @typecheck
    def created(cls, *, secret: Secret) -> tuple["SecretEvent", Secret]:
        return cls(_kind=SecretEventKind.CREATED, secret=secret), secret   # (atomic, aggregate)

    @classmethod
    @typecheck
    def updated(cls, *, secret: Secret) -> tuple["SecretEvent", Secret]:   # 모든 팩토리 (atomic, entity)
        return cls(_kind=SecretEventKind.UPDATED, secret=secret), secret

    # #
    # query  (emit이 duck-typed로 읽음)

    def act(self) -> str:             return self._kind.value
    def act_entity_name(self) -> str: return "secret"
    def act_entity_id(self) -> UUID:  return self.secret.id
    def payload(self) -> dict:        return {"domain": ..., "service": ..., "project": ..., "field": ...}
```

- id는 `created()` 시점 확정(`default_factory=uuid4`) → `AtomicEvent.from_atomic(atomic=..., ...)`로 발행본·저장본 identity 일치
- 명명 팩토리 `created`/`updated`/`deleted`/`rotated`/`read` — `@classmethod @typecheck`, sync. 모두 `(atomic, aggregate)` 2-튜플 반환 → 호출부 `event, x = SecretEvent.factory(...)`로 통일(이미 손에 있어 entity가 필요 없으면 `event, _ =`). 단 `rotated`는 Team 엔티티가 없어 둘째 원소가 `team_id`
- 배치 팩토리 `{act}_many` — list 입력(`read_many`/`create_many`/…)은 `list[tuple[atomic, entity]]` 반환(=단건 `(atomic, entity)`를 리스트에 map). atomic은 단일 엔티티 유지(`AtomicEvent` 1행 = `act_entity_id` 1개) — "여럿"은 atomic 안의 list가 아니라 atomic N개 + 같은 `event_id`로 표현(emit이 호출당 1개 스탬프). 호출부는 언집: `atomics=[event for event, _ in founds]`(emit) / `[x.to_dict() for _, x in founds]`(return). 현재는 `read_many`만 소비처 있음(list usecase) — `create_many`/`update_many`는 배치 write usecase가 생기면 같은 형태로 추가([Simplicity First], 미리 만들지 않음)
- 접근자 `id()`/`act()`/`act_entity_name()`/`act_entity_id()`/`payload()` — `emit`이 duck-typed로 읽어 `AtomicEvent`(엔티티 인덱스 + payload)로 변환. 모두 필수 계약(누락 시 `emit`이 `AttributeError`). atomic엔 `team_id()`도 `to_dict()`도 없다 — 테넌트는 emit이 스탬프, 응답 echo는 *저장된* `AtomicEvent.to_dict()`
- `payload()`는 비밀값 금지 — 평문 식별자만(`secret`이면 domain/service/project/field, `account`면 email, `token`이면 account_id). 복호화된 value·salt·verifier·team_locked_key 등 민감값은 절대 싣지 않는다(payload는 JSONB 평문 저장)

---

## 저장 — `EventRepository.emit` (루트 + 자식)

이벤트 저장은 두 aggregate로 분업한다 — `domain/event/event/`(`event.py`의 `Event(Entity)`: name/status/attempts(reaction 완료 ledger, JSONB)/claimed_at/succeeded_at/failed_at, `event_repository.py`의 `EventModel`+`EventRepository`)와 `domain/event/atomic_event/`(`atomic_event.py`의 `AtomicEvent(Entity)`: event_id/act/act_entity_name/act_entity_id/payload/actor_id/actor_team_id/sequence, `atomic_event_model.py`의 `AtomicEventModel`+매퍼). dispatch 상태는 루트 `Event`가, 엔티티 인덱스 + `payload`(소비 스냅샷, JSONB)는 자식 `AtomicEvent`가 가진다. 자식은 별도 repository 없이 루트 `EventRepository`가 직접 영속·조회(`emit`/`filter_by_event_id`)를 소유한다 — child entity가 root aggregate 경유로만 접근되는 DDD 원칙 그대로.

```python
class EventRepository(PostgresRepository[Event, EventModel]):
    model = EventModel
    mapper = _to_event

    @classmethod
    async def emit(cls, *, session, id, name, atomics, actor_id=None, actor_team_id=None) -> list[AtomicEvent]:
        # event (idempotent upsert — name + dispatch 상태만, payload 없음)
        await session.execute(
            pg_insert(cls.model)
            .values(**Event.new(id=id, name=EventName.from_str(name)).to_model())
            .on_conflict_do_nothing(index_elements=["id"])
        )
        # atomic (엔티티 인덱스 + 자기 payload, from_atomic이 atomic.payload()를 담음)
        entities = [
            AtomicEvent.from_atomic(atomic=atomic, event_id=id, actor_id=actor_id, actor_team_id=actor_team_id)
            for atomic in atomics
        ]
        models = [AtomicEventModel(**entity.to_model()) for entity in entities]
        session.add_all(models)
        await session.flush()
        return [_to_atomic_event(model) for model in models]

    @classmethod
    async def filter_by_event_id(cls, *, session, event_id) -> list[AtomicEvent]:
        result = await session.scalars(
            select(AtomicEventModel)
            .where(AtomicEventModel.event_id == event_id, AtomicEventModel.deleted_at.is_(None))
            .order_by(AtomicEventModel.sequence.asc())
        )
        return [_to_atomic_event(model) for model in result]
```

- atomic=목적어+동사+평문, emit=주어+묶음 스탬프 — `actor_id`/`actor_team_id`/`id`(=`event_id`)는 usecase가 요청 맥락에서 전달(`id`는 behavior `Scope`가 요청당 1개 생성해 스레딩), `name`은 usecase가 자기 이름(파일명 스템)을 직접 넘긴다. emit은 받은 값을 스탬프만, payload는 각 atomic이 자기 것을 `AtomicEvent`에 그대로 들고 간다(병합 없음) — atomic은 "누가/어느 묶음"을 몰라도 됨([INV-7] 유지)
- 저장 whitelist 동기화 의무: `entity_name.py`의 `EntityName._allowed_list`와 `act.py`의 `Act._allowed_list`가 모든 atomic의 `act_entity_name()`/`{Aggregate}EventKind` 값을 미러링해야 한다. 새 atomic·act 추가 시 atomic enum + 두 `_allowed_list` 갱신 — 누락 시 `emit`의 `from_str()`가 `InvalidFormatError`로 거부
- `emit`은 저장만 — `events`는 묶음의 dispatch 상태(pending/claimed/succeeded/failed), `atomic_events`는 도메인 변경과 같은 트랜잭션에 쓰는 append-only 엔티티 인덱스 + payload(어느 엔티티가 어떻게 변했나 + 그 소비 스냅샷)다. 커밋 후 worker가 `Event.name`으로 라우팅해 atomic마다 reaction을 실행한다(아래 dispatch). 실패는 atomic에 안 담김(raise → 롤백 → atomic 소멸) — 실패 감사는 별도 logger
- read 이벤트도 write처럼 응답에 echo(`event=[...]`) — read/write 응답 shape 일관
- `actor_team_id`는 테넌트 격리(RLS — `atomic_events`는 `actor_team_id`가 테넌트 컬럼). global(RLS 밖) 동작이면 `None`. `actor_id`도 미인증(register)이면 `None`. `sequence`는 DB Identity 단조 커서(id/audit 처럼 raw, `to_model` 제외)

---

## 조정 — usecase + Output 응답 — [INV-8]

도메인 변경 + 이벤트 저장의 조정은 usecase 책임. atomic + `emit`을 같은 session으로 = atomic. `account_id`는 behavior가 yield한 `Scope`(`context.account_id`, context splitter로 주입)에서 usecase로 흘러 emit의 `actor_id=`로 전달 — actor 추상은 event에서만 산다:

```python
# write — 도메인 변경 + atomic (모든 팩토리 (atomic, entity) 튜플)
event, entity = SecretEvent.created(
    secret=await SecretRepository.add(session=session, entity=Secret.new(...)),
)
return Output(
    data=entity.to_dict(),
    event=[e.to_dict() for e in (await EventRepository.emit(
        session=session, id=event_group_id, name="secret_create", atomics=[event],
        actor_id=account_id, actor_team_id=team_id))],
)

# read(조회) — 성공 접근 기록 + write처럼 echo. atomic이 fetch 를 감싼다(write 의 created 와 동형)
event, secret = SecretEvent.read(
    secret=await SecretRepository.get_by_id(session=session, id=..., team_id=team_id))
return Output(
    data={**secret.to_dict(), "value": secret.value.to_str()},
    event=[e.to_dict() for e in (await EventRepository.emit(
        session=session, id=event_group_id, name="secret_reveal", atomics=[event],
        actor_id=account_id, actor_team_id=team_id))],
)
```

- actor_id(atomic_event 컬럼): 인증된 account(`membership.account_id`/`account.id`). usecase는 `account_id: UUID | None = None` 파라미터로 받아 emit의 `actor_id=`로 전달(CLI는 미전달 → None). register는 미인증 → None
- actor_team_id: usecase의 `team_id` 스코프(member-scoped면 team_id, global이면 None)
- `id`(emit의 `Event.id`, usecase 파라미터명은 현재 `event_group_id`): behavior `Scope`가 요청당 1개 생성 → endpoint가 `event_group_id=`로 주입, usecase가 emit의 `id=`로 전달(CLI는 `_main`에서 `uuid4()`)
- `name`(emit의 `Event.name`): usecase가 자기 파일명 스템(`"secret_create"`)을 emit의 `name=`에 리터럴로 — usecase가 자기 이름의 단일 출처라 HTTP/CLI 양 경로 일관
- read 이벤트도 write처럼 응답에 echo(`event=[...]`) — data(조회 결과) + event(접근 기록) 둘 다 응답에

---

## payload — consumer 자족 (fat), 각 AtomicEvent에 적재

reaction(아래 dispatch)은 **emit 시점 atomic의 `payload`만으로** 동작한다 — 비동기 처리 시 엔티티가 이미 바뀌거나 삭제됐을 수 있어 콜백(재로드)하지 않는다(event-carried state transfer). 각 `AtomicEvent.payload`는 그 atomic의 `payload()` 평문 스냅샷이라, reaction이 필요로 하는 평문을 다 담는다.

- sibling aggregate 평문은 **조정자(usecase)가 공급** — atomic은 자기 aggregate만 안다([INV-7]). 다른 aggregate 값(초대받는이 `email`·`team_name`)이 필요하면 usecase가 로드해 atomic 팩토리에 raw로 넘기고, atomic은 받아 담기만(IO·타 aggregate import 0). VO로 받으면 그 aggregate에 의존하므로 **raw(`str` 등)** 로.
- 공급된 경우만 payload에 — reaction 없는 경로(team_create founder 멤버십 등)는 미공급 → 생략.
- 민감값 금지는 그대로 — value·salt·key 등은 payload 불가(그런 값이 필요한 reaction은 없어야 함).
- 1:N은 collection 아니라 **per-entity atomic N개**로 — N명 알림은 payload에 list를 싣지 말고 atomic N개를 같은 `event_id`로 emit(각자 자기 멤버 평문으로 자족). dispatch가 그 atomic들을 순회하며 reaction을 N번. atomic 1개가 곧 reaction 1회라 payload 병합(키 겹침·last-wins)이 없다.
- `AtomicEvent.payload`는 flat — reaction의 `from_event(atomic)`가 필요한 키를 직접 꺼낸다.

## dispatch — reaction (event-triggered usecase)

커밋 후 behavior가 `Event.dispatch_event`로 worker를 깨운다(NOTIFY = wake hint, 내구성은 outbox=`events`+claim). worker 쪽 UoW(claim→scope→yield→succeed/fail)가 단일 row를 claim한 뒤 `usecase/event_dispatch.dispatch(id=...)`를 호출, 그 Event의 atomic들을 `filter_by_event_id`로 sequence 순 로드해 atomic마다 reaction `Input.from_event(atomic)`로 넘겨 실행한다(N fan-out). 각 unit(reaction×atomic) 결과(succeeded/failed)를 `Event.attempts` ledger에 기록하고 끝에 한 번 persist — UoW·등록 디테일은 [behavior.md](behavior.md)·[endpoint-internal.md](endpoint-internal.md) 참고.

- dispatch key = **`Event.name`**(= 도메인 이벤트, "어느 usecase가 일어났나"). 같은 atomic이라도 Event마다 의미가 달라 Event 단위 라우팅 — team_invite의 `team_access.created`(초대) ≠ team_create의 것(founder).
- reaction = **usecase 레이어의 event-triggered usecase** — `usecase/<reaction>.py`에 `Input(EventIn)` + `async def run(*, session, input)`. `Input`은 필드 + `from_event(atomic)`를 직접 구현 — base `EventIn`은 계약만(`raise NotImplementedError`), 각 reaction이 atomic `payload`에서 자기 필드를 명시적으로 꺼낸다(= 그 reaction이 요구하는 payload 키 명세). boundary 입력 `In`과 달리 이벤트가 먹이는 입력이라 별도 base `EventIn`(`core/usecase.py`). 호출자만 endpoint 대신 worker.
- dispatch는 Event의 atomic 전체를 순회 — reaction은 매칭되는 atomic마다 1회. 한 Event의 atomic이 동종일 때 안전(이종이 섞이면 reaction의 `from_event`가 자기 키만 읽도록 custom).
- registry는 `usecase/event_dispatch.py`의 `EVENT_COMMANDS` — `{Event.name: [reaction]}`. 미등록(조회 usecase 등) → no-op.
- claim = 동시성 가드 — `EventRepository.claim(*, session, id)`가 `status=pending` 조건부 단일 UPDATE로 atomic하게 가져간다(0 row 반환 = 다른 worker가 이미 가져갔거나 처리됨 → skip). `pg_notify`는 broadcast라 여러 worker가 같은 id를 동시에 받을 수 있어 claim 없이는 reaction이 중복 실행된다.
- 멱등 = **`Event.attempts` ledger**(`{reaction: {atomic_id: {status, count, error}}}`, JSON). reaction 실패는 raise 없이 ledger에 `failed`로 기록, 다른 unit을 막지 않는다. 재dispatch 시 `succeeded` unit은 skip → 끝난 발송 중복 안 함(at-least-once 위 per-unit 멱등). 인프라(dispatch 단위) 실패만 `Event.fail`을 타 `_dispatch` 키에 기록 + status 전이. 묶음 claim/tenant scope는 `event_id`·NOTIFY payload `team_id`(`Tenant.set_tenant_scope` 재사용, BYPASS 아님, global은 NULL).

---

## 안티패턴

- atomic이 IO/async를 갖거나 다른 aggregate repo·entity를 호출·반환 → atomic은 순수 (**[INV-7]**). 저장은 `emit`, 조정은 usecase. 단 consumer 자족용 sibling 평문은 조정자가 raw로 공급(위 payload)
- reaction 로직을 action usecase·domain에 합침 → reaction은 별 usecase(event-triggered), registry로만 연결(action↔reaction 분리)
- payload를 루트 `Event`에 (묶음 단일 스냅샷) → payload는 각 `AtomicEvent`가 자기 것을 소유. 그래야 1:N fan-out에서 entity별 평문이 안 뭉개짐(merge·last-wins 금지). 루트 `Event`는 dispatch 상태만
- 1:N을 payload list로 한 atomic에 → per-entity atomic N개 + 같은 `event_id`. dispatch가 N번 순회
- reaction이 저장된 평문 대신 엔티티를 재로드 → event-carried state transfer, `Input.from_event(atomic)`로 atomic payload에서 읽기
- payload에 민감값(value·salt·key) → 평문만
- atomic이 `actor`/`team`/묶음 id를 안다 → 그건 요청 맥락, emit이 스탬프. atomic은 목적어+동사+평문만
- 저장된 `AtomicEvent` id를 DB가 새로 발급 → atomic `id()`(`created()` 시점 확정)를 `AtomicEvent.from_atomic`로
- atomic에 `to_dict()` 추가 → 응답은 저장된 `AtomicEvent.to_dict()`를 echo하므로 atomic `to_dict()`는 죽은 코드
- `{Aggregate}EventKind` 값과 저장 `act`가 다른 vocabulary(`"CREATED"` vs `"created"`) → 표기 단일화, `kind_map` 금지. 대상은 `act_entity_name`으로 분리(점표기 `"secret.created"` 한 컬럼에 욱여넣기 금지)
- 이벤트 저장을 각 aggregate repo에 흩뿌리기 → 단일 `domain/event` 루트(`Event`)+자식(`AtomicEvent`) aggregate(`emit`)로 집약
- global(RLS 밖) 동작의 이벤트에 actor_team_id 채우기 → `None`(usecase가 전달 안 함)
- read의 `event`를 `None`으로 (echo 누락) → read도 write처럼 `event=[...]`로 echo
- 응답을 맨몸 dict로 → `Output(data, event)` ([INV-8])
