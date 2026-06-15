# Domain Event 패턴

도메인 행위가 낳는 이벤트를 **세 군데로 분업** — 마커(domain·순수) / 저장(`EventRepository.emit`·event aggregate) / 조정(usecase). 마커는 `emit`을 직접 호출하지 않는다.

루트: [api.md](../api.md) · entity: [entity.md](entity.md) · repo: [repository.md](repository.md) · 흐름: [usecase-flow.md](usecase-flow.md)

---

## 이 문서

| 섹션 | 핵심 규칙 |
|------|----------|
| **마커 (domain)** | `Event` 상속 순수 마커, IO/async·타 aggregate 의존 0 — **[INV-7]** |
| **저장 (event aggregate)** | `EventRepository.emit`이 마커 → `Event` entity 변환 후 일괄 add |
| **조정 (usecase)** | 도메인 변경 + 마커 + `emit`(같은 session) + 인라인 dict 응답 — **[INV-8]** |
| **vocabulary** | `{Aggregate}EventKind` 값 = action 표기 `"created"`, `EntityAction._allowed_list` 미러링. entity는 `entity_name`(`"secret"`)으로 분리 |

---

## 마커 — 순수 (domain) — [INV-7]

`{aggregate}_event.py`에 산다. `core/event.py`의 `Event`(`_id` + `id()`만 가진 frozen 마커 base) 상속, **IO·async·다른 aggregate 의존 0.**

```python
# domain/secret/secret_event.py
@dataclass(frozen=True, kw_only=True)
class SecretEvent(Event):
    _kind: SecretEventKind         # Enum, 값은 action "created" (entity_name 은 마커가 상수로)
    secret: Secret

    # #
    # factory  (@classmethod @typecheck, sync)

    @classmethod
    @typecheck
    def created(cls, *, secret: Secret) -> tuple["SecretEvent", Secret]:
        return cls(_kind=SecretEventKind.CREATED, secret=secret), secret   # (마커, aggregate)

    @classmethod
    @typecheck
    def updated(cls, *, secret: Secret) -> "SecretEvent":   # deleted 동일
        return cls(_kind=SecretEventKind.UPDATED, secret=secret)

    # #
    # query  (emit이 duck-typed로 읽음)

    def entity_name(self) -> str:   return "secret"
    def entity_action(self) -> str: return self._kind.value
    def entity_id(self) -> UUID:    return self.secret.id
    def payload(self) -> dict:      return {"domain": ..., "service": ..., "project": ..., "key": ...}
    def to_dict(self) -> dict:      return {"entity_name": "secret", "entity_action": self._kind.value, "secret_id": str(self.secret.id)}
```

- **id는 `created()` 시점 확정**(`default_factory=uuid4`) → `Event.new(id=마커.id())`로 발행본·저장본 identity 일치
- **명명 팩토리** `created`/`updated`/`deleted` — `@classmethod @typecheck`, **sync**, persist된 aggregate를 받음. persist 호출을 감싸는 `created`/`deleted`는 `(마커, aggregate)` 튜플, aggregate가 이미 손에 있는 `updated`는 단일 마커
- **접근자** `id()`/`entity_name()`/`entity_action()`/`entity_id()`/`payload()` — `emit`이 duck-typed로 읽어 `Event` entity로 변환. **모두 필수 계약** — 새 마커는 반드시 구현(누락 시 `emit`이 `AttributeError`)
- **`payload()`는 비밀값 금지** — 평문 메타데이터만(`secret`이면 domain/service/project/key, `vault`면 `{}`). 복호화된 value·salt·wrapped_dek 등 민감값은 절대 싣지 않는다(payload는 JSONB 평문 저장)

---

## 저장 — `EventRepository.emit` (event aggregate)

이벤트 저장 자체가 하나의 aggregate(`domain/event/`): `event.py`(`Event(Entity)`), `entity_name.py`/`entity_action.py`/`status.py`(`_allowed_list` enum VO), `event_repository.py`(`EventModel` + `EventRepository`).

```python
class EventRepository(PostgresRepository[Event, EventModel]):
    model = EventModel
    mapper = _to_event

    @classmethod
    async def emit(cls, *, session, events: list) -> list[Event]:
        return await cls.add_many(session=session, entities=[
            Event.new(id=e.id(), entity_name=EntityName.from_str(e.entity_name()),
                      entity_action=EntityAction.from_str(e.entity_action()),
                      entity_id=e.entity_id(), payload=Payload.from_dict(e.payload()))
            for e in events
        ])
```

- **저장 whitelist 동기화 의무**: `entity_name.py`의 `EntityName._allowed_list`와 `entity_action.py`의 `EntityAction._allowed_list`가 **모든 마커의 `entity_name()`/`{Aggregate}EventKind` 값을 미러링**해야 한다. 새 마커·action 추가 시 마커 enum + 두 `_allowed_list` 갱신 — 누락 시 `emit`의 `from_str()`가 `InvalidFormatError`로 거부
- dispatch(소비/외부 발행)는 **별도 관심사** — `emit`은 저장만 책임
- **`events`는 outbox 겸 감사 로그**: 도메인 사실(`entity_name`/`entity_action`/`entity_id`/`payload`)은 INSERT 후 불변, **배달 상태**(`status`/`succeeded_at`/`failed_at`/`error`)만 워커가 갱신. `sequence`는 DB Identity 단조 커서(id/audit 처럼 raw, `to_model` 제외)

---

## 소비 — outbox 워커 (별도 프로세스)

`emit`이 같은 트랜잭션에 이벤트를 쓰는 것 = transactional outbox의 "적기". "배달"은 **요청 경로 밖** [bin/worker.py](../../../personal_secret/api/bin/worker.py)가 책임 — `events`를 폴링해 부수효과를 실행한다.

```
[요청 tx]  도메인 변경 + emit(같은 session) ── 원자적
[워커 tx]  claim_pending(FOR UPDATE SKIP LOCKED, sequence순) → dispatch(핸들러) → succeed / fail
```

- **상태기계**: `pending → succeeded | failed` (엔티티 전이 `succeed()`/`fail()`). claim은 `pending`만 집음 → `failed`는 종착(**재시도 비허용** — 멈춘 이벤트는 수동 복구)
- **한 배치 = 한 트랜잭션**: claim + mark 원자적, 잠금은 커밋까지(`SKIP LOCKED`로 다중 워커 안전)
- **at-least-once**: 핸들러 성공 후 커밋 실패 시 재배달 가능 → **핸들러는 멱등**해야 함
- **핸들러 레지스트리**: `infrastructure/outbox/handler.py`의 `HANDLERS`에 추가(현재 감사 로그 JSONL). 조정은 `usecase/outbox/drain.py`
- **설정**: `config.py`의 `OutboxConfig`(poll interval / batch / audit path)

---

## 조정 — usecase + 인라인 응답 — [INV-8]

도메인 변경 + 이벤트 저장의 조정은 usecase 책임. 마커 + `emit`을 **같은 session**으로 = atomic.

```python
# 도메인 변경 + 마커 (created는 (마커, aggregate) 튜플)
event, entity = SecretEvent.created(
    secret=await SecretRepository.add(session=session, entity=Secret.new(...)),
)

# 저장 + 인라인 응답 (Output 래퍼 없음)
return {
    "data": entity.to_dict(),
    "event": [e.to_dict() for e in (await EventRepository.emit(session=session, events=[event]))],
}
```

`event`는 저장된 이벤트 리스트(한 usecase가 여러 이벤트를 낼 수 있어 리스트).

---

## 안티패턴

- ❌ 마커가 IO/async를 갖거나 다른 aggregate repo·entity를 호출·반환 → 마커는 **순수** (**[INV-7]**). 저장은 `emit`, 조정은 usecase
- ❌ 저장된 `Event` id를 DB가 새로 발급 → 마커 `id()`(`created()` 시점 확정)를 `Event.new(id=...)`로
- ❌ `{Aggregate}EventKind` 값과 저장 `entity_action`이 다른 vocabulary(`"CREATED"` vs `"created"`) → action 표기 단일화, `kind_map` 금지. entity는 `entity_name`으로 분리(점표기 `"secret.created"` 한 컬럼에 욱여넣기 금지)
- ❌ 이벤트 저장을 각 aggregate repo에 흩뿌리기 → 단일 `domain/event` aggregate(`emit`)로 집약
- ❌ 응답을 `Output` 래퍼로 → 인라인 dict (**[INV-8]**)
