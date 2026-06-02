# Python Architecture

`franchise_manager/api/` 레이어 구조 + 의존 방향 + 반복 패턴.

목적: "동작을 어디에 둘지 / 새 파일을 만들지" 같은 판단을 매번 새로 하지 않도록 기준 고정.

---

## 레이어

```
endpoint        ← HTTP 진입 (FastAPI route handlers)
usecase         ← 비즈니스 흐름 (deps + input → output)
domain          ← 비즈니스 모델 (Entity / ValueObject / Repository wiring)
infrastructure  ← 외부 시스템 어댑터 (HTTP 클라이언트 / DB / 캐시 + repository 일반화)
core            ← 베이스 추상 (Entity / ValueObject / UseCase / Repository / Event / Base / typecheck)
```

## 의존 방향

- ✅ **위에서 아래로만** import (endpoint → usecase → domain → infrastructure)
- ✅ 모든 레이어 → `core` OK
- ✅ 같은 레이어 형제 모듈 import OK
- ❌ 역방향 (infrastructure → domain, domain → usecase 등) 금지

**예외 — 의도적 완화** (DDD purity vs. 코드 양 트레이드오프):
- `domain/{aggregate}/{aggregate}_repository.py`에 SQLAlchemy `Model` 동거
- domain → `infrastructure/postgresql/repository` import 허용 (`PostgresRepository` 상속)
- 사유: KV repo 한 도메인 때문에 별도 infrastructure 파일 만들 가치 없음

---

## 각 레이어 책임

### core/
ABC + 데이터클래스 베이스, 데코레이터.

| 파일 | 내용 |
|------|------|
| `entity.py` | Entity 베이스 (`id: UUID` + `by_factory` 가드) |
| `value_object.py` | ValueObject 베이스 (`by_factory` 가드) |
| `usecase.py` | UseCase 베이스 |
| `repository.py` | Generic abstract `Repository[T]` — **classmethod** abstract (add / get_by_id / update / remove_by_id) |
| `event.py` | DomainEvent 베이스 (`Event` — 빈 frozen dataclass) |
| `model.py` | SQLAlchemy `Base` |
| `validate.py` | `@typecheck` 데코레이터 |
| `exception.py` | 예외 루트 — `ApplicationError`(`msg`/`code` + `__trace_back__`) + 2분류 `ClientError`(4xx) / `DevelopError`(5xx). **모든 예외의 단일 진입점** |

**`by_factory` 가드 설명:**
- `Entity(id=..., by_factory=False)` ❌ 직접 생성 불가능
- `Entity.new(...)` ✓ 팩토리 메서드만 허용
- 목적: DDD Entity 생성 규칙 강제 (검증 + 불변성 보장)

거의 변화 없음. 외부 라이브러리는 SQLAlchemy `Base` 정도만.

### domain/{aggregate}/
비즈니스 모델 + 도메인-specific 데이터.

| 파일 | 내용 |
|------|------|
| `{value}.py` | ValueObject (`Key`, `Value`, `Name` 등) — frozen dataclass + factory |
| `{aggregate}.py` | Entity (`Setting`, `Brand` 등) — frozen dataclass + `new` 팩토리 + `to_dict` / `to_model` |
| `{aggregate}_repository.py` | SQLAlchemy `Model` + concrete `Repository` (**classmethod wiring만, 메서드 본문 0개가 목표**) |
| `{aggregate}_event.py` | 도메인 이벤트 **마커** (`{Aggregate}EventKind` enum + `{Aggregate}Event` — 순수, IO 0) |

**event aggregate** (`domain/event/`) — 이벤트 저장 자체가 하나의 aggregate:
- `event.py` — `Event(Entity)` (`kind`/`entity_type`/`entity_id`) + `new(*, id, ...)` (id는 마커가 넘김)
- `kind.py` / `entity_type.py` — `_allowed_list` enum 성격 VO
- `event_repository.py` — `EventModel` + `EventRepository` with `emit(*, session, events)` (마커 리스트 → `Event.new` → `add_many`)

**원칙**:
- Entity/VO는 frozen dataclass + factory 강제 (`by_factory`)
- Repository는 `PostgresRepository[Entity, Model]` 상속 + class variables(`model`/`mapper`) 정의 — 메서드는 전부 **`@classmethod`** (인스턴스/싱글톤 없음)
- 도메인-specific 동작이 부모에 일반화되어 있으면 wiring만으로 사용
- 일반화 안 된 도메인 동작만 domain repository에 직접 구현 (`@classmethod`)
- 도메인 이벤트 마커는 `{aggregate}_event.py`에 — 순수(IO 0). 저장은 `EventRepository.emit`, dispatch는 별도

**구현 패턴**: [python-style.md](./python-style.md) "DDD 도메인" 섹션 참고

### infrastructure/{system}/
외부 시스템 어댑터. **동작 일반화의 책임처**.

| 파일 | 내용 |
|------|------|
| `client.py` | 외부 API 호출 클래스 + 모듈 레벨 싱글톤 (`cafe24 = Cafe24(...)`) |
| `cache.py` | in-memory 캐시 클래스 + 싱글톤 |
| `postgresql/repository.py` | Generic concrete `PostgresRepository[T, M]` — CRUD + KV 일반 동작 |
| `postgresql/session.py` | 트랜잭션 헬퍼 |
| `crypto/client.py` | `crypto` 싱글톤 — 키 파생 + blob `encrypt`/`decrypt`(nonce+ciphertext 포맷 소유) |
| `crypto/cache.py` | `session_cache` 싱글톤 — DEK 캐시(sliding TTL) + `encrypt`/`decrypt`(잠겨있으면 `LockedError`) |
| `common/exception.py` | infra 레이어 예외 — `InfrastructureError(DevelopError)` ← `DatabaseError`/`CryptoError`(500) + `LockedError(ClientError)`(423) |

**원칙**:
- 도메인이 wiring만 하도록 충분히 유연한 부모 클래스 설계 책임이 여기 있음
- 싱글톤은 직접 모듈 변수 (factory 함수 wrapper X) — [python-style.md](./python-style.md) "Infrastructure 싱글톤" 참고
- **예외는 레이어 `common/exception.py`에 모은다** — 서브모듈(`crypto/` 등)에 별도 `exception.py`를 두지 않는다 ([예외 구조](#예외-구조) 참고)
- **암호화 메커니즘은 infra 안에 숨긴다**: usecase는 `session_cache.encrypt(plaintext=...) -> bytes` / `decrypt(data=...) -> bytes`만 본다. DEK 조회·lock 확인(없으면 `LockedError`)은 `session_cache`, nonce 포맷·AEAD는 `crypto`가 소유. 도메인은 결과 blob을 `Ciphertext.from_bytes(bytes=...)`로 감쌀 뿐 — 단일 blob VO(`to_bytes`/base64 `to_str`)라 crypto 내부 포맷을 모른다

### usecase/{aggregate}/
비즈니스 흐름 — deps + input → output.

| 파일 | 내용 |
|------|------|
| `{action}.py` | `Input` pydantic 모델 + `@typecheck async def {action}(...)` 함수 + `# cli` 섹션 |

**원칙**:
- 함수 시그니처: `(*, session, input: Input) -> Result`
- repository는 **클래스 자체**를 import — 클래스 메서드로 직접 호출 (`from ... import SecretRepository` → `SecretRepository.add(...)`) — 인스턴스화 X
- 모든 repo 호출에 `session=session`을 명시적으로 주입 (같은 session = atomic transaction)
- 외부 시스템 싱글톤(`cafe24`, `oauth_*_cache`, `session_cache` 등)은 모듈 import로 직접 사용
- 도메인 동작은 repository 메서드 호출 — **usecase에 persistence helper(`_upsert` 등) 두지 말 것** (domain repo로 끌어올리기)
- 도메인 이벤트는 **마커**(`{Aggregate}Event`)로 만들고 **`EventRepository.emit(session=session, events=[마커])`**(event aggregate)로 저장 — 도메인 변경 + 이벤트 저장의 조정은 usecase 책임. 응답은 인라인 dict(`{"data": ..., "event": [...]}`)로 조합 (패턴 5 참고)

### endpoint/
FastAPI route handlers. usecase 호출 + HTTP 응답 변환. 비즈니스 로직 0.

---

## 반복 패턴

### 패턴 1. Repository (classmethod + session-per-method)

모든 도메인 repository는 **classmethod 모음**. 인스턴스/싱글톤 없이 **클래스 자체로 호출** (`SecretRepository.add(...)`). session은 모든 메서드 호출의 `session=` kwarg로 받음.

**구조**: class variables (`model`, `mapper`) 정의 + base의 `@classmethod`들이 `cls.model`/`cls.mapper`로 동작 (`__init__`/`__init_subclass__` 없음). 커스텀 finder는 `@classmethod`로 base의 **일반 query 코어에 위임**:
- `_filter(*, equals/lte/gte/in_/like, order_by, descending, limit, offset)` — filter + sort + pagination 한 곳에 일반화 (전 조건 AND, `deleted_at IS NULL` 자동)
- `_find(...)` 단건 / `_count(...)` int / `_page(*, limit, offset, ...) -> (items, total)` 페이지
- 단일 컬럼 sugar `_find_by` / `_filter_by` / `_filter_by_all`(다중 equality) / `_exists_by`(bool) — 전부 위 코어로 위임

**호출 형태**:
```python
from personal_secret.api.domain.secret.secret_repository import SecretRepository

secret = await SecretRepository.add(session=session, entity=Secret.new(...))
found  = await SecretRepository.find_by_name(session=session, name=name)
```

**제네릭이 타입 좁힘**: `class SecretRepository(PostgresRepository[Secret, SecretModel])`라서 `SecretRepository.add(...)`의 반환은 이미 `Secret`. passthrough override 불필요.

**`mapper` 바인딩 주의**: `mapper = _to_secret`(클래스 변수 함수)는 `cls.mapper(model)`로 **언바운드 호출**됨 — `cls`(인스턴스 아님) 경유라 `self`가 안 끼인다. 그래서 classmethod에서 안전.

**판정 기준 — 부모 vs 자식**:
- entity 1개에만 쓰이고 일반화 어려움 → domain repository classmethod로
- 2개 이상 entity에 패턴 반복 → `PostgresRepository`에 끌어올리기 + entity 컨벤션 합의

**상세 구현**: [python-style.md](./python-style.md) "DDD 도메인 / Repository 패턴" 섹션 참고

### 패턴 2. UseCase (함수 + Input)

`usecase/{aggregate}/{action}.py` — Input 모델 + 함수 + CLI

**시그니처**: `async def {action}(*, session, input: Input) -> Result`

**원칙**:
- repository는 **클래스로 import** — 호출 시 `SecretRepository.add(session=session, ...)`
- persistence helper는 domain repository 메서드로 끌어올리기

**상세 구현**: [python-style.md](./python-style.md) "UseCase 파일 구조" 섹션 참고

### 패턴 3. Infrastructure 싱글톤

외부 시스템 어댑터(`cafe24`, `oauth_*_cache` 등)는 모듈 수준 직접 인스턴스화 — factory 함수 wrapper 금지.

(**repository는 싱글톤 아님** — classmethod 클래스 자체로 호출. 패턴 1 참고.)

**상세 구현**: [python-style.md](./python-style.md) "Infrastructure 싱글톤" 섹션 참고

### 패턴 4. Session = Transaction 경계 (usecase 1개 = 1 트랜잭션)

Repository는 **stateless classmethod 모음**. session은 **모든 호출의 첫 kwarg**. 같은 session을 모든 repo 호출에 주입하면 같은 transaction.

```
transactional_session(SessionLocal)
   │ BEGIN
   ├─ session 생성
   ├─ yield session                                  ← usecase 실행 구간
   │     ├─ SecretRepository.add(session=session, ...)
   │     ├─ VaultRepository.add(session=session, ...)
   │     └─ 같은 session 주입한 모든 쿼리 = 같은 transaction
   │ COMMIT (정상) / ROLLBACK (예외)
   │ session close
```

**usecase에서 지킬 contract**:
- `session`을 인자로 받음 — usecase 안에서 새로 만들지 말 것
- 모든 repo 메서드 호출에 **같은 session 주입**:
  ```python
  async def some_usecase(*, session, input):
      await SecretRepository.add(session=session, entity=secret)
      await EventRepository.emit(session=session, events=[event])
      # → 두 호출 atomic
  ```
- usecase 내부에서 `session.commit()` / `session.begin()` 명시적 호출 금지 — outer `transactional_session`이 관리

**session 생성 위치**:
- FastAPI endpoint: `Depends(transactional_session_helper)`
- CLI `_main`: `async with transactional_session(db_client.SessionLocal) as session:`

**transaction에 포함 안 되는 것** (별도 commit 흐름 따로 고려):
- 외부 HTTP (`cafe24.exchange_code` 등) — 이미 발생한 호출은 rollback 불가. usecase 내 ordering: HTTP → DB 순서로 두면 DB 실패 시 outer state 일관 유지 가능
- in-memory cache (`oauth_token_cache.set` 등) — DB commit 이후 시점이 안전하지만 현재는 commit이 usecase return 후이라 cache가 commit 전 갱신될 여지 있음. admin tool 수준에서는 허용

**왜 session을 메서드 인자로 받는가** (classmethod를 가능하게 하는 핵심):
- repo가 session-바인딩 인스턴스면 매 요청마다 `Repo(session=...)` 생성 필요 → classmethod 불가
- session-per-method로 받으면 repo는 stateless → 인스턴스 없이 **classmethod로 클래스 자체 호출** 가능
- 호출 시 `session=` 명시가 noise 같지만 **transaction boundary가 호출부에서 보이는** 이점
- repo classmethod 호출 + 인프라 싱글톤(cafe24, oauth_*_cache) 모두 모듈 import 후 직접 호출이라 일관

### 패턴 5. Domain Event (순수 마커 + event aggregate 저장 + 인라인 응답)

도메인 행위가 낳는 이벤트를 **세 군데로 분업**한다:
- **마커** `domain/{aggregate}/{aggregate}_event.py` — `core/event.py`의 `Event` 상속, **순수**(IO·다른 aggregate 의존 0). "무슨 일이 일어났나"만 표현
- **저장** `domain/event/`의 `EventRepository.emit` — 마커 리스트를 `Event` entity로 변환해 `add_many` (이벤트 저장도 하나의 aggregate)
- **조정** usecase — 도메인 변경 + `EventRepository.emit` + 인라인 응답 dict 조합

> 마커는 `EventRepository.emit`을 직접 호출하지 않는다. 도메인 변경과 이벤트 저장을 한 transaction에 묶는 조정은 application(usecase) 레이어 책임이다.

**마커 구조** (`SecretEvent` 기준):
- `core/event.py`의 `Event`(`_id` + `id()` 접근자만 가진 frozen 마커 base) 상속 — **identity는 명명 팩토리 호출 시점에 확정**(`default_factory=uuid4`)
- `{Aggregate}EventKind(Enum)` — 값은 `{entity}.{eventname}` 점 표기 (`"secret.created"`)
- 필드: `_kind: {Aggregate}EventKind` + `{aggregate}: {Aggregate}` (entity 보유)
- **명명 팩토리** `created`/`updated`/`deleted` — `@classmethod @typecheck`, **sync**
- **접근자** `id()`(base) / `kind()` / `entity_type()` / `entity_id()` — `emit`이 duck-typed로 읽어 `Event.new(id=마커.id(), ...)`로 변환 (**마커 id = 저장된 Event id**, 동작 직후 발행본과 DB 저장본이 같은 identity)
- `to_dict()` — 직렬화

**저장** (`EventRepository.emit`, event aggregate):
```python
@classmethod
async def emit(cls, *, session, events: list) -> list[Event]:
    return await cls.add_many(session=session, entities=[
        Event.new(id=e.id(), kind=Kind.from_str(e.kind()),
                  entity_type=EntityType.from_str(e.entity_type()), entity_id=e.entity_id())
        for e in events
    ])
```

**usecase 호출 형태**:
```python
# 도메인 변경 + 마커 (created는 (마커, aggregate) 튜플 반환)
event, entity = SecretEvent.created(
    secret=await SecretRepository.add(session=session, entity=Secret.new(...)),
)

# 저장(event aggregate) + 인라인 응답
return {
    "data": entity.to_dict(),
    "event": [e.to_dict() for e in (await EventRepository.emit(session=session, events=[event]))],
}
```

**원칙**:
- 마커는 **순수** — IO/async 없음, 다른 aggregate repo/entity 의존 0 (조정은 usecase가)
- 저장은 **`EventRepository.emit`** — usecase가 `session=` 명시로 호출(도메인 변경과 같은 transaction = atomic)
- 응답은 **인라인 dict**(`{"data": ..., "event": [...]}`) — `Output` 같은 래퍼 클래스 없음. `event`는 저장된 이벤트 리스트(한 usecase가 여러 이벤트를 낼 수 있어 리스트)
- dispatch(소비/외부 발행)는 **별도 관심사** — `emit`은 저장만 책임

---

## 예외 구조

예외는 **레이어별 `common/exception.py`에 모으고, 모든 예외는 `ClientError` 또는 `DevelopError`를 (직·간접) 상속**한다.

```
core/exception.py
  ApplicationError(Exception)        msg·code + __trace_back__   ← 직접 raise 안 함
  ├─ ClientError                     4xx · 클라이언트 책임
  └─ DevelopError                    5xx · 서버 책임

domain/common/exception.py
  DomainError(ClientError)           레이어 베이스
  ├─ InvalidError / InvalidFormatError   400
  ├─ NotFoundError                       404
  └─ AlreadyExistsError                  409

infrastructure/common/exception.py
  InfrastructureError(DevelopError)  레이어 베이스
  ├─ DatabaseError / CryptoError         500
  └─ LockedError(ClientError)            423   ← 4xx라 레이어 베이스 우회, ClientError 직접 상속
```

**핸들러 (`server/exception.py`)** — 2개로 4xx/5xx 완결:
- `client()` → `ClientError` 등록. `exc.code`(400~423) 그대로 응답, dev에서만 traceback 첨부
- `internal()` → **`Exception` 등록(catch-all)**. `ClientError` 외 **모든 예외**(`DevelopError`·raw DB 오류·`RuntimeError` 등)를 500으로. 항상 로그(`error_id` + traceback), dev에서만 응답에 상세 노출, 그 외 마스킹 + `error_id`만
- Starlette가 `type(exc).__mro__`로 가장 구체적인 핸들러를 고르므로 `ClientError`는 `client()`, 나머지는 `internal()`로 자동 분기

**원칙**:
- **레이어당 예외 파일은 `common/exception.py` 하나** — 서브모듈(`crypto/` 등)에 별도 `exception.py`를 만들지 않는다
- **`core/exception.py`는 루트 전용** — `ApplicationError` + 2분류(`ClientError`/`DevelopError`)만. 구체 예외는 두지 않는다. core 내부 가드(`by_factory`/`typecheck`)는 새 클래스 없이 **`DevelopError`를 메시지와 함께 직접 raise**
- **모든 구체 예외는 `ClientError`/`DevelopError`로 귀결** — 보통 레이어 베이스(`DomainError`/`InfrastructureError`)를 거치되, HTTP 성격(4xx vs 5xx)이 레이어 기본과 다르면 해당 분류를 **직접 상속**(예: infra의 `LockedError`는 423이라 `ClientError` 직접 상속)
- **미처리 예외는 `internal()` catch-all이 받는다** — 단 raw 오류는 발생 경계에서 typed 예외로 변환: DB는 `transactional_session`에서 `SQLAlchemyError → DatabaseError`, crypto는 `crypto/client.py`에서 `Exception → CryptoError`
- 구체 예외만 `message`/`code`를 채운다 — 베이스(`...`)는 분류용 마디

---

## 의사결정 체크리스트

새 기능 추가 / 기존 동작 이동 시 순서대로 점검:

1. **이 동작은 entity 1개에만 쓰이나?**
   - YES → domain repository 메서드로
   - NO → infrastructure 부모(`PostgresRepository`)로 끌어올리기 + entity 컨벤션(`with_X`, `new(*, key, value)`) 갖추기

2. **이 helper는 usecase 안 흐름 조립인가, 도메인 모델의 동작인가?**
   - 흐름 조립 → usecase 함수 안 인라인 또는 모듈 레벨 `_helper`
   - 도메인 모델 동작 → domain repository / entity 메서드로 끌어올리기

3. **이 싱글톤은 환경별 분기가 필요한가?**
   - YES → factory 함수 (`get_postgres_config()` 같이)
   - NO → 직접 모듈 변수 (`cafe24 = Cafe24(...)`)

4. **이 import는 레이어 방향 맞나?**
   - 위에서 아래만 OK. 의심되면 의존 그래프 그려보기

5. **새 파일을 만들기 전: 기존 파일에 동거 가능한가?**
   - 도메인 repo concrete impl은 `infrastructure/postgresql/{aggregate}_repository.py` 같은 중간 파일 만들지 말고 `domain/{aggregate}/{aggregate}_repository.py`에 동거
   - 싱글톤 여러 개도 한 파일에 (e.g. `cache.py`의 `OAuthStateCache` + `OAuthTokenCache`)

---

## 안티패턴

- ❌ usecase에 `_upsert` 같은 persistence helper → domain repo 공개 메서드(`set_by_key`)로
- ❌ domain repo에 `find_by_X` 직접 SQL (`select(...).where(...)`) → `PostgresRepository._filter`/`_find`/`_count` (또는 sugar `_find_by`/`_filter_by`/`_filter_by_all`)로 delegate
- ❌ fetch 후 파이썬 후필터/정렬/슬라이싱(`[x for x in ...]`, `sorted(...)`, `[:n]`) → `_filter`의 `equals/lte/.../like` + `order_by` + `limit`/`offset`으로 **DB-side 처리** (페이지는 `_page`로 items+total)
- ❌ usecase에서 존재 확인을 `find_by_X(...) is not None`로 (entity 전체 fetch) → repo `exists_by_X`(`_exists_by` delegate, count 기반 `bool`). 존재 여부만 필요하면 entity를 떠오지 말 것 (raise는 usecase가, 존재 쿼리는 repo가 책임)
- ❌ domain repo `__init__` / `__init_subclass__` 구현 — repo는 classmethod 모음. `model`/`mapper` class variable만 정의
- ❌ domain repo 메서드를 인스턴스 메서드(`self`)로 — 전부 `@classmethod`(`cls`). session은 메서드 인자
- ❌ repo 싱글톤 인스턴스(`secret_repository = SecretRepository()`) / usecase에서 인스턴스화(`repo = SecretRepository(...)`) — 클래스 자체로 `SecretRepository.add(...)` 호출
- ❌ base CRUD passthrough override(`async def add(...): return await super().add(...)`) — 제네릭이 이미 타입 좁힘. 본문 있는 도메인 가드일 때만 override
- ❌ domain repo가 추상(`abstractmethod`) 메서드만 갖고 concrete impl이 별도 파일 — `PostgresRepository` 직접 상속해서 한 파일로
- ❌ `infrastructure/postgresql/{aggregate}_repository.py` 중간 파일 — domain repo가 직접 상속
- ❌ factory 함수 wrapper로 (인프라) 싱글톤 노출 → 직접 모듈 변수
- ❌ Entity에 `.update_value(value)` 같은 mutating 메서드 — frozen이므로 `.with_value(value)` evolve
- ❌ repo 메서드 호출 시 `session=` 빠뜨림 — 모든 호출에 명시 (transaction boundary 가시화)
- ❌ 도메인 이벤트 마커(`SecretEvent` 등)가 IO/async를 갖거나 다른 aggregate의 repository·entity를 호출·반환 — 마커는 **순수**(factory/접근자 모두 sync, 의존 0). 저장은 `EventRepository.emit`, 조정은 usecase
- ❌ 저장된 `Event` id를 DB가 새로 발급 — 마커 `id()`(`created()` 시점 확정)를 `Event.new(id=...)`로 넘겨 발행본·저장본 identity 일치
- ❌ `{Aggregate}EventKind` 값과 저장되는 `kind`가 다른 vocabulary(`"CREATED"` vs `"secret.created"`) — 점 표기 단일화. 둘을 잇는 `kind_map` 금지
- ❌ usecase 응답을 `Output.response(...)` 같은 래퍼로 — 인라인 dict(`{"data": ..., "event": [...]}`)로 직접 조합
- ❌ 이벤트 저장을 각 aggregate repo에 흩뿌리기 — 저장은 단일 `domain/event` aggregate(`EventRepository.emit`)로 집약. 각 도메인엔 순수 마커만
- ❌ 서브모듈에 별도 예외 파일(`crypto/exception.py` 등) — 예외는 레이어 `common/exception.py`에 집약 ([예외 구조](#예외-구조))
- ❌ `core/exception.py`에 구체 예외(`message`/`code` 보유) 추가 — 루트엔 `ApplicationError` + `ClientError`/`DevelopError`만. 구체 예외는 `ClientError`/`DevelopError`를 상속해 레이어 `common/exception.py`에

---

## 참조

- [python-style.md](./python-style.md) — 코드 컨벤션 (네이밍 / 섹션 마커 / CLI / Import 등)
- [system.md](./system.md) — 공통 워크플로우 (MCP 의존성 확인)
