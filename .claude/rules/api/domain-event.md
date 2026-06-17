---
paths:
  - "personal_secret/api/**/*_event.py"
  - "personal_secret/api/domain/event/**"
  - "personal_secret/api/core/event.py"
---

# Domain Event 패턴

도메인 행위가 낳는 이벤트를 세 군데로 분업 — 마커(domain·순수) / 저장(`EventRepository.emit`·event aggregate) / 조정(usecase). 마커는 `emit`을 직접 호출하지 않는다. `events`는 트랜잭션 내 append-only 도메인 사실 + 성공 접근(success/access) 로그 — 도메인 변경과 같은 트랜잭션에 원자적으로 기록된다. 따라서 실패/거부는 담기지 않는다(repo 오류·`raise`는 롤백되어 이벤트도 사라짐). 실패/시도 감사(인증 실패·권한 거부)는 트랜잭션 밖 별도 logger 채널의 몫 — 이 테이블에 섞지 않는다.

스키마 문법은 주어-동사-목적어: `actor_id`(주어)가 `actor_team_id`에서 `act`(동사)를 `act_entity_name`/`act_entity_id`(목적어)에 했고, 한 액션은 `act_group_id`로 묶인다. read(조회)도 `act="read"`로 기록되는 성공 접근 신호다.

루트: [api/CLAUDE.md](../../../personal_secret/api/CLAUDE.md) · entity: [entity.md](entity.md) · repo: [repository.md](repository.md) · 흐름: [usecase-flow.md](usecase-flow.md)

---

## 이 문서

| 섹션 | 핵심 규칙 |
|------|----------|
| 마커 (domain) | `Event` 상속 순수 마커, IO/async·타 aggregate 의존 0 — [INV-7]. "무엇에 무슨 행위"(목적어+동사)만 안다 |
| 저장 (event aggregate) | `EventRepository.emit`이 마커 → `Event` entity 변환 + actor 스탬프 후 일괄 add |
| 조정 (usecase) | 도메인 변경 + 마커 + `emit`(같은 session, actor 전달) + `Output.new(data, event)` 응답 — [INV-8] |
| vocabulary | `{Aggregate}EventKind` 값 = `act` 표기(`"created"`/`"read"`), `Act._allowed_list` 미러링. 대상은 `act_entity_name`(`"secret"`)으로 분리 |

---

## 마커 — 순수 (domain) — [INV-7]

`{aggregate}_event.py`에 산다. `core/event.py`의 `Event`(`_id` + `id()`만 가진 frozen 마커 base) 상속, IO·async·다른 aggregate 의존 0. 모든 write/read aggregate가 자기 마커를 가진다. 마커는 목적어+동사만 — 누가(`actor_id`)·어느 팀(`actor_team_id`)·묶음(`act_group_id`)은 요청 맥락이라 `emit`이 채운다.

```python
# domain/secret/secret_event.py
@dataclass(frozen=True, kw_only=True)
class SecretEvent(Event):
    _kind: SecretEventKind         # Enum, 값은 act "created"/"read" (act_entity_name 은 마커가 상수로)
    secret: Secret

    # #
    # factory  (@classmethod @typecheck, sync)

    @classmethod
    @typecheck
    def created(cls, *, secret: Secret) -> tuple["SecretEvent", Secret]:
        return cls(_kind=SecretEventKind.CREATED, secret=secret), secret   # (마커, aggregate)

    @classmethod
    @typecheck
    def updated(cls, *, secret: Secret) -> tuple["SecretEvent", Secret]:   # 모든 팩토리 (마커, entity)
        return cls(_kind=SecretEventKind.UPDATED, secret=secret), secret

    # #
    # query  (emit이 duck-typed로 읽음)

    def act(self) -> str:             return self._kind.value
    def act_entity_name(self) -> str: return "secret"
    def act_entity_id(self) -> UUID:  return self.secret.id
    def payload(self) -> dict:        return {"domain": ..., "service": ..., "project": ..., "field": ...}
```

- id는 `created()` 시점 확정(`default_factory=uuid4`) → `Event.new(id=마커.id())`로 발행본·저장본 identity 일치
- 명명 팩토리 `created`/`updated`/`deleted`/`rotated`/`read` — `@classmethod @typecheck`, sync. 모두 `(마커, aggregate)` 2-튜플 반환 → 호출부 `event, x = Marker.factory(...)`로 통일(이미 손에 있어 entity가 필요 없으면 `event, _ =`). 단 `rotated`는 Team 엔티티가 없어 둘째 원소가 `team_id`
- 배치 팩토리 `{act}_many` — list 입력(`read_many`/`create_many`/…)은 `list[tuple[마커, entity]]` 반환(=단건 `(마커, entity)`를 리스트에 map). 마커는 단일 엔티티 유지(`Event` 1행 = `act_entity_id` 1개) — "여럿"은 마커 안의 list가 아니라 마커 N개 + 같은 `act_group_id`로 표현(emit이 호출당 1개 스탬프). 호출부는 언집: `events=[event for event, _ in founds]`(emit) / `[x.to_dict() for _, x in founds]`(return). 현재는 `read_many`만 소비처 있음(list usecase) — `create_many`/`update_many`는 배치 write usecase가 생기면 같은 형태로 추가([Simplicity First], 미리 만들지 않음)
- 접근자 `id()`/`act()`/`act_entity_name()`/`act_entity_id()`/`payload()` — `emit`이 duck-typed로 읽어 `Event` entity로 변환. 모두 필수 계약(누락 시 `emit`이 `AttributeError`). 마커엔 `team_id()`도 `to_dict()`도 없다 — 테넌트는 emit이 스탬프, 응답 echo는 *저장된* `Event.to_dict()`
- `payload()`는 비밀값 금지 — 평문 식별자만(`secret`이면 domain/service/project/field, `account`면 email, `token`이면 account_id). 복호화된 value·salt·verifier·team_locked_key 등 민감값은 절대 싣지 않는다(payload는 JSONB 평문 저장)

---

## 저장 — `EventRepository.emit` (event aggregate)

이벤트 저장 자체가 하나의 aggregate(`domain/event/`): `event.py`(`Event(Entity)`), `act.py`(`Act`)·`entity_name.py`(`EntityName`)·`payload.py`(VO), `event_repository.py`(`EventModel` + `EventRepository`).

```python
class EventRepository(PostgresRepository[Event, EventModel]):
    model = EventModel
    mapper = _to_event

    @classmethod
    async def emit(cls, *, session, events, actor_id=None, actor_team_id=None) -> list[Event]:
        act_group_id = uuid4()                       # 한 emit(=한 액션) 묶음
        return await cls.add_many(session=session, entities=[
            Event.new(id=e.id(), act=Act.from_str(e.act()),
                      act_entity_name=EntityName.from_str(e.act_entity_name()),
                      act_entity_id=e.act_entity_id(), payload=Payload.from_dict(e.payload()),
                      act_group_id=act_group_id, actor_id=actor_id, actor_team_id=actor_team_id)
            for e in events
        ])
```

- 마커=목적어+동사, emit=주어+묶음 — `actor_id`/`actor_team_id`는 usecase가 요청 맥락에서 전달, `act_group_id`는 emit이 호출당 1개 생성. 마커는 "누가 봤는지"를 몰라도 됨([INV-7] 유지)
- 저장 whitelist 동기화 의무: `entity_name.py`의 `EntityName._allowed_list`와 `act.py`의 `Act._allowed_list`가 모든 마커의 `act_entity_name()`/`{Aggregate}EventKind` 값을 미러링해야 한다. 새 마커·act 추가 시 마커 enum + 두 `_allowed_list` 갱신 — 누락 시 `emit`의 `from_str()`가 `InvalidFormatError`로 거부
- `emit`은 저장만 — `events`는 도메인 변경과 같은 트랜잭션에 쓰는 append-only 성공/접근 로그. 별도 배달·dispatch 없음. 실패는 안 담김(raise → 롤백 → 이벤트 소멸) — 실패 감사는 별도 logger
- read 이벤트도 응답 echo 안 함 — 조회 결과가 응답, 감사는 side-record
- `actor_team_id`는 테넌트 격리(RLS — `events`는 `actor_team_id`가 테넌트 컬럼). global(RLS 밖) 동작이면 `None`. `actor_id`도 미인증(register)이면 `None`. `sequence`는 DB Identity 단조 커서(id/audit 처럼 raw, `to_model` 제외)

---

## 조정 — usecase + Output 응답 — [INV-8]

도메인 변경 + 이벤트 저장의 조정은 usecase 책임. 마커 + `emit`을 같은 session으로 = atomic. actor는 endpoint(`require_member`/`require_owner`의 membership)에서 usecase로 흘려 emit에 전달:

```python
# write — 도메인 변경 + 마커 (모든 팩토리 (마커, entity) 튜플)
event, entity = SecretEvent.created(
    secret=await SecretRepository.add(session=session, entity=Secret.new(...)),
)
return Output.new(
    data=entity.to_dict(),
    event=[e.to_dict() for e in (await EventRepository.emit(
        session=session, events=[event], actor_id=actor_id, actor_team_id=team_id))],
)

# read(조회) — 성공 접근 기록, 응답엔 echo 안 함. 마커가 fetch 를 감싼다(write 의 created 와 동형)
event, secret = SecretEvent.read(
    secret=await SecretRepository.get_by_id(session=session, id=..., team_id=team_id))
await EventRepository.emit(
    session=session, events=[event], actor_id=actor_id, actor_team_id=team_id)
return Output.new(
    data={**secret.to_dict(), "value": secret.value.to_str()},
    event=None,
)
```

- actor_id: 인증된 account(`membership.account_id`/`account.id`). usecase는 `actor_id: UUID | None = None` 파라미터로 받고 emit에 전달(CLI는 미전달 → None). register는 미인증 → None
- actor_team_id: usecase의 `team_id` 스코프(member-scoped면 team_id, global이면 None)
- read 이벤트는 응답에 echo하지 않는다 — 조회 결과(데이터)가 응답이고 감사는 side-record

---

## 안티패턴

- 마커가 IO/async를 갖거나 다른 aggregate repo·entity를 호출·반환 → 마커는 순수 (**[INV-7]**). 저장은 `emit`, 조정은 usecase
- 마커가 `actor`/`team`/`act_group`을 안다 → 그건 요청 맥락, emit이 스탬프. 마커는 목적어+동사만
- 저장된 `Event` id를 DB가 새로 발급 → 마커 `id()`(`created()` 시점 확정)를 `Event.new(id=...)`로
- 마커에 `to_dict()` 추가 → 응답은 저장된 `Event.to_dict()`를 echo하므로 마커 `to_dict()`는 죽은 코드
- `{Aggregate}EventKind` 값과 저장 `act`가 다른 vocabulary(`"CREATED"` vs `"created"`) → 표기 단일화, `kind_map` 금지. 대상은 `act_entity_name`으로 분리(점표기 `"secret.created"` 한 컬럼에 욱여넣기 금지)
- 이벤트 저장을 각 aggregate repo에 흩뿌리기 → 단일 `domain/event` aggregate(`emit`)로 집약
- global(RLS 밖) 동작의 이벤트에 actor_team_id 채우기 → `None`(usecase가 전달 안 함)
- read 이벤트를 응답에 echo → 감사는 side-record, 응답은 조회 데이터만
- 응답을 맨몸 dict로 → `Output.new(data, event)` ([INV-8])
