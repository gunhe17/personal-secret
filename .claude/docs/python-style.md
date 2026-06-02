# Python Code Style

worship-support의 Python 코드 컨벤션. 모든 Python 파일에 적용.

---

## 파일 구조

**모듈 docstring 작성하지 않는다.** 파일명, `# #` 섹션, 최상위 함수가 의도를 드러낸다.

**절차 순서 = 읽기 순서.** 호출자가 위, 피호출자가 아래. 최상위 함수가 파일 맨 위. 타입(`@dataclass` 등)은 그 단계 섹션 안에 동거. 전방 참조용 `from __future__ import annotations` 사용.

**모듈 수준 상수 블록(`MAX_X = ...`)은 피한다.** 별도 `config.py`로 분리 (`ABC` + `@property @abstractmethod` + 환경별 서브클래스 + 팩토리 함수). 단일 파일 lab/script의 `# config` 섹션은 fallback이지 권장 아님.

**CLI 섹션 최대한 간결**:
- `argparse.ArgumentParser()` 빈 생성자 (description은 필요할 때만)
- `_main` = parse → side-effect → delegate
- 단발 입력은 kwarg에 인라인 (중간 변수 X)
- 위임 결과는 직접 `return await ...`
- 섹션 내 순서: `_parse_args` → `_main` → `if __name__`
- **`# cli` 섹션 내부는 함수 사이 빈 줄 1줄** (모듈 기본 2줄의 예외 — CLI 진입부는 시각적으로 한 단락)
- 리소스 셋업(session 등)은 wrapper 함수 분리하지 말고 `_main` 안에 `async with`로 인라인

```python
from __future__ import annotations

import argparse
import asyncio


# #
# orchestrate

async def generate(*, ...) -> list[ScoredSong]:
    # fetch
    metadatas = await fetch_all_metadata(...)
    # score
    scored = [score(...) for m in metadatas]
    # select
    generated = select(scored=scored, size=size)

    return generated


# #
# fetch
# (SongMetadata 타입, fetch 관련 함수들)

# #
# score
# (ScoredSong 타입, score 관련 함수들)

# #
# select
# (select 관련 함수들)

# #
# cli

def _parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser().parse_args()

async def _main():
    _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(start_oauth(
            session=session,
            input=Input.new(),
        ))

if __name__ == "__main__":
    asyncio.run(_main())
```

---

## 섹션 마커

**`# #` 시그니처**로 파일/클래스 내부 논리 영역 구분.

```python
# #
# factory

@classmethod
def new(cls, ...): ...
```

라벨 예:
- 모듈: `# route`, `# run`, `# cli`, `# client`, `# model`, `# repository`, `# orchestrate`, `# fetch`, `# score`, `# select`
- 클래스 내부: `# factory`, `# query`, `# command`, `# create`, `# read`, `# update`, `# delete`

**인라인 라벨(`# label`, 단일 `#`)** 로 메서드 내부 단계 표기.

```python
# type
if not isinstance(value, str):
    raise  # InvalidError

# format
if not re.match(...):
    raise  # InvalidFormatError
```

라벨 예: `# type`, `# format`, `# value`, `# length`, `# hint`, `# cap`, `# normalize`, `# components`, `# weighted sum`, `# fan-out`, `# filter`, `# backoff retry`, `# rank`, `# fallback`.

---

## 네이밍

**식별자에 폴더/파일 컨텍스트를 중복하지 않는다.** 호출부 `from foo.bar import X`에서 경로 `foo.bar`가 이미 컨텍스트를 제공함. `X` 안에 `foo`나 `bar`를 다시 담으면 import 라인이 `bar의 BarX`처럼 stutter.

**폴더 컨텍스트 중복 금지** (폴더명을 접두로 반복하지 않음):

```
infrastructure/cafe24/cache.py
  class Cafe24OAuthStateCache  ❌  →  class OAuthStateCache  ✓
  def cafe24_token_cache()     ❌  →  def token_cache()      ✓

usecase/cafe24/start_oauth.py
  class StartCafe24OAuth       ❌  →  class StartOAuth       ✓
```

**파일 컨텍스트 중복 금지** (파일명을 접미/접두로 반복하지 않음):

```
setlist_generator.py
  def generate_setlist()       ❌  →  def generate()         ✓

domain/user/email.py
  def from_email_str()         ❌  →  def from_str()         ✓
```

**예외 — 파일 안에 동종 다중 식별자가 있어 분별 단어가 필요한 경우**:

```
infrastructure/cafe24/cache.py
  class OAuthStateCache, class OAuthTokenCache    # "Cache" 보존 (둘 다 캐시), "OAuth" 일관 부여

domain/brand/brand_repository.py
  class BrandModel, class BrandRepository         # "Model"/"Repository" 보존
```

이 경우엔 분별 단어(`Cache`, `Model`, `Repository`)는 유지하되 폴더 prefix(`Brand`, `Cafe24`)는 유지/생략 모두 가능. 베이스 ABC가 일반 이름(`Repository`, `Entity`)일 때만 서브에 도메인 prefix 부여로 충돌 회피 (예: `BrandRepository extends Repository`).

| 대상 | 형태 | 예 |
|------|------|-----|
| 클래스 | PascalCase | `User`, `RegisterUser` |
| 함수/메서드/변수 | snake_case | `from_str`, `user_repository` |
| 비공개 (모듈/필드) | `_` 접두 | `_value`, `_fetch_metadata` |
| Config 프로퍼티 | UPPER_CASE | `POSTGRES_USER` |
| 힌트 클래스 필드 | `_` + `# hint` | `_format: str = "%Y-%m-%d"` |

---

## 반환값

**Happy path는 named variable에 담은 뒤 return.** 함수의 정상 출력을 함수 이름을 만족하는 변수에 담고 반환.

```python
metadata = SongMetadata(...)
return metadata
```

**예외**:
- 가드/에러 early return: inline (`return None`, `return 0.0` 등)
- 순수 위임(passthrough): `return await delegate(...)` inline 허용 (CLI 진입점 등)

| 함수 | 변수명 |
|------|--------|
| `fetch_all_metadata` | `metadatas` |
| `_fetch_metadata` | `metadata` |
| `_fetch_with_retry` | `response` |
| `score` | `scored` |
| `_score_freshness` | `freshness` |
| `select` | `selected` |
| `generate` | `generated` |

규칙: intermediate 변수는 **생산 함수** 출력 의미, 최종 return 변수는 **enclosing 함수** 출력 의미.

---

## 호출 스타일

**인자 표기는 all-or-nothing.** 한 호출 안에서 keyword/positional 혼용 금지.

```python
# ✓ 전부 positional
asyncio.wait_for(coro, FETCH_TIMEOUT_SEC)
random.sample(["a", "b", "c"], 2)

# ✓ 전부 keyword
score(metadata=m, target_topics=topics, congregation_low=lo, congregation_high=hi)

# ❌ 혼용
asyncio.wait_for(coro, timeout=FETCH_TIMEOUT_SEC)
random.sample(["a", "b"], k=2)
```

stdlib 강제 혼용 예외:
- `sorted(iterable, /, *, key, reverse)`
- `argparse.add_argument(*name_or_flags, **kwargs)`

**키워드 전용 강제.** 도메인 함수는 `*` 로 모든 인자 키워드 전용화. 다인자 시그니처는 파라미터마다 줄바꿈 + trailing comma.

```python
def new(
    cls,
    *,
    name: Name,
    birth: Birth,
    email: Email,
    password: Password,
) -> "User":
```

**인자 값이 nested call이면 호출을 펼친다.** 호출 인자 값이 그 자체로 팩토리/변환 호출(`Name.from_str(...)`, `Tags.from_list(...)`, `Ciphertext.from_bytes(...)` 등)이면 한 줄에 욱여넣지 말고 **인자마다 줄바꿈 + trailing comma**로 펼친다. nested 변환이 한눈에 들어오고, 인자가 하나여도 동일하게 적용.

```python
# ✓ nested call 인자 → 펼침
if await SecretRepository.exists_by_name(
    session=session,
    name=Name.from_str(input.name),
):
    raise AlreadyExistsError("Secret", input.name)

# ❌ 한 줄에 욱여넣기 — nested 변환이 묻힌다
if await SecretRepository.exists_by_name(session=session, name=Name.from_str(input.name)):
    raise AlreadyExistsError("Secret", input.name)
```

- 트리거는 **인자 값에 nested call이 있는지** — 전부 단순 값(`session=session`, `id=secret.id`)이면 한 줄 유지 OK
- 펼친 형태는 정의부와 동일하게 **trailing comma** 유지 (위 "키워드 전용 강제" 규칙과 일관)

---

## DDD 도메인 (worship_support/api/)

**Dataclass + Factory 강제.** 모든 도메인 클래스 `@dataclass(frozen=True, kw_only=True)`. 베이스가 `by_factory` 플래그로 직접 생성 차단.

```python
@dataclass(frozen=True, kw_only=True)
class ValueObject:
    by_factory: InitVar[bool] = False

    def __post_init__(self, by_factory: bool):
        if not by_factory:
            raise  # Error
```

서브클래스는 `cls.new(...)` 또는 `cls.from_str(...)` 팩토리만 사용.

**팩토리 메서드**:
- `@classmethod` + `@typecheck`
- `*` 키워드 전용
- 반환 타입 = forward reference 문자열 (`"User"`)
- ValueObject = `from_str`, Entity/UseCase = `new`

**예외 처리.** 구체 예외 클래스 미구현 시 **bare `raise` + 의도 주석**으로 자리 표시.

```python
raise  # InvalidError
raise  # AlreadyExistsError
```

**Repository 패턴** — class variables 정의 + 전 메서드 `@classmethod` (인스턴스/싱글톤 없음, 클래스 자체로 호출):

```python
# (a) 순수 wiring — base classmethod 가 cls.model/cls.mapper 로 동작
class BrandRepository(PostgresRepository[Brand, BrandModel]):
    model = BrandModel
    mapper = _to_brand

# (b) 커스텀 finder (1줄 delegation) — classmethod + cls
class UserRepository(PostgresRepository[User, UserModel]):
    model = UserModel
    mapper = _to_user

    @classmethod
    async def find_by_phone(cls, *, session, phone: Phone) -> User | None:
        return await cls._find_by(session=session, column="phone", value=phone.to_str())
```

호출은 클래스 자체로:
```python
secret = await SecretRepository.add(session=session, entity=Secret.new(...))
user   = await UserRepository.find_by_phone(session=session, phone=phone)
```

**도메인 repo가 가져야 할 것**:
- Class variables: `model` (필수), `mapper` (필수)
- 모든 메서드 **`@classmethod`** — base 상속 메서드(`add`/`get_by_id`/...)는 그대로 클래스 호출, 커스텀은 `(cls, *, session, ...)` + `_find_by` / `_filter_by` / `_exists_by`(존재여부 bool, count 기반) delegation
- mapper 함수(`_to_X`)는 모듈 중간
- 모듈 끝에 **싱글톤 인스턴스 두지 않음** — 클래스가 곧 호출 대상

**도메인 repo가 가지면 안 될 것**:
- `__init__` / `__init_subclass__` 구현 — repo는 classmethod 모음, `model`/`mapper` class variable만
- 인스턴스 메서드(`self`) / 싱글톤 인스턴스(`x_repository = XRepository()`) — 전부 `@classmethod`, 클래스로 호출
- base CRUD passthrough override(`add` → `super().add`) — 제네릭이 이미 타입 좁힘. 본문 있는 도메인 가드일 때만 override
- 직접 SQL → `_find_by` / `_filter_by` / `_exists_by` 위임
- `_upsert` 등 persistence helper → domain repo classmethod로 끌어올리기
- 존재 확인을 위해 `find_by_X`로 entity를 떠와 `is not None` 비교 → `exists_by_X`(count 기반 `bool`)로. entity가 실제로 필요 없으면 fetch 금지

**CRUD 메서드 명명** (부모 `PostgresRepository`에서 제공):
- 생성: `add`, `add_many`
- 조회(public): `get_by_id`, `get_by_ids`, `exists_by_id`, `list_all`(조건 없는 전체)
- 조회 코어(protected, 도메인 finder가 위임): `_filter`(equals/lte/gte/in_/like + `order_by`/`descending` + `limit`/`offset`) / `_find`(단건) / `_count`(int) / `_page`(`limit`,`offset` → `(items, total)`) / sugar `_find_by`·`_filter_by`·`_filter_by_all`·`_exists_by`
- 수정: `update`, `update_many`
- 삭제: `remove_by_id`, `remove_by_ids`

**write 메서드는 DB 반영 entity를 반환한다** (`add -> E`, `add_many -> list[E]`, `update -> E | None`, `update_many -> list[E]`, `remove_by_id -> E`):
- `add`는 `flush` 후 server_default(`created_at`/`updated_at`)가 채워진 model을 매퍼로 변환해 반환
- `update`/`remove_by_id`는 `... RETURNING <model>`로 갱신/soft-delete된 행을 한 문장에 받아 반환 (soft-delete 행은 `deleted_at IS NULL` 필터에 걸려 재조회가 안 되므로 RETURNING이 정답).
  - **`remove_by_id`는 `.one()`** — 대상이 없으면 raise(`NoResultFound`), 있으면 `removed` 반환. usecase가 먼저 `find_by_identifier`로 존재 확인(404)하므로 raise는 사실상 race 가드
  - **`update`는 `.first()`+`None`** — usecase가 `None` 가드로 `NotFoundError` 변환(race-safe)
- usecase는 반환 entity를 받아 `to_dict()` — 생성/수정 응답에도 타임스탬프가 일관되게 실린다 (`secret = await repo.add(...); secret.to_dict()`)
- exists는 의도(존재여부)대로 `bool` 유지 — write 아님

**KV 패턴** (set_by_key / set_by_keys 쓰려면):
- entity: `.new(*, key, value)` + `.with_value(value) -> Self`
- model: `key` 컬럼
- repo: `entity = Entity` 와이어

**bulk vs 단건**:
- N=1 → `set_by_key` (단순)
- N≥2 → `set_by_keys(pairs=...)` (1 SELECT IN + add_many + update_many)

**ValueObject 패턴** — 단순 값 (str, int) vs 복합 값 (dict):

```python
# 단순 값 — from_str / to_str
@dataclass(frozen=True, kw_only=True)
class Name(ValueObject):
    _value: str
    @classmethod
    def from_str(cls, value) -> "Name":
        if not isinstance(value, str) or not value.strip():
            raise InvalidFormatError("Name")
        return cls(_value=value, by_factory=True)
    def to_str(self) -> str:
        return self._value

# 복합 값 — from_dict / to_dict
@dataclass(frozen=True, kw_only=True)
class Address(ValueObject):
    _text: str
    _latitude: float
    _longitude: float
    @classmethod
    def from_dict(cls, value) -> "Address":
        if not isinstance(value, dict):
            raise InvalidError("Address")
        text = value.get("text")
        if not isinstance(text, str) or not text.strip():
            raise InvalidFormatError("Address.text")
        latitude = float(value.get("latitude"))
        if not (-90.0 <= latitude <= 90.0):
            raise InvalidFormatError("Address.latitude")
        return cls(_text=text, _latitude=latitude, _longitude=float(value.get("longitude")), by_factory=True)
    def to_dict(self) -> dict:
        return {"text": self._text, "latitude": self._latitude, "longitude": self._longitude}
```

```python
# 시간 값 — from_datetime / to_str + to_datetime
@dataclass(frozen=True, kw_only=True)
class OccurredAt(ValueObject):
    _value: datetime
    @classmethod
    def from_datetime(cls, value) -> "OccurredAt":
        if not isinstance(value, datetime):
            raise InvalidError("OccurredAt")
        return cls(_value=value, by_factory=True)
    def to_str(self) -> str:        # API 직렬화 (to_dict)
        return self._value.isoformat()
    def to_datetime(self) -> datetime:  # DB 저장 (to_model)
        return self._value

# enum 성격 값 — 허용값을 _allowed_list hint로 분리
@dataclass(frozen=True, kw_only=True)
class Role(ValueObject):
    _value: str

    # hint
    _allowed_list: tuple[str, ...] = ("super_admin", "viewer")

    @classmethod
    def from_str(cls, value) -> "Role":
        if not isinstance(value, str):
            raise InvalidError("Role")
        # format
        if value not in cls._allowed_list:
            raise InvalidFormatError("Role")
        return cls(_value=value, by_factory=True)
    def to_str(self) -> str:
        return self._value

# bool 플래그 — from_bool / to_bool
@dataclass(frozen=True, kw_only=True)
class IsChecked(ValueObject):
    _value: bool
    @classmethod
    def from_bool(cls, value) -> "IsChecked":
        if not isinstance(value, bool):   # isinstance(1, bool) == False → int 거부
            raise InvalidError("IsChecked")
        return cls(_value=value, by_factory=True)
    def to_bool(self) -> bool:
        return self._value
```

**ValueObject 원칙**:
- **frozen dataclass + kw_only** 강제
- **필드명 `_` 접두** (private)
- **팩토리**: `from_str` (단순) / `from_dict` (복합) / `from_datetime` (시간) / `from_bool` (플래그) / `from_int` (수량·금액)
- **변환**: `to_str` / `to_dict` / `to_bool` / `to_int` (+ 시간 VO는 DB용 native 접근자 `to_datetime` 추가)
- **검증 순서**: type (InvalidError) → format (InvalidFormatError) → range/규칙

**datetime은 raw stdlib 타입으로 두지 않는다.** Entity의 모든 datetime 필드는 VO로 승격(aggregate별 VO 파일 — `occurred_at.py` → `OccurredAt`). `to_dict`에서 `.isoformat()` 직접 호출 금지 — VO의 `to_str()` 쿼리 메서드 사용. `to_model`은 native가 필요하므로 `to_datetime()`을 사용.
- 단순/복합 VO는 String/JSONB 컬럼이라 `to_model`도 `to_str()`/`to_dict()` 그대로지만, 시간 VO는 `DateTime` 컬럼이라 `to_model`만 `to_datetime()`로 갈린다
- 예외: `created_at` / `updated_at` / `deleted_at`은 **VO로 승격하지 않고 raw `datetime`으로 `Entity` 베이스([core/entity.py](../../personal_secret/api/core/entity.py))에 둔다** — `id`가 raw `UUID`로 베이스에 있는 것과 같은 결. 매퍼가 로드 시 채우고(`created_at=model.created_at`), `to_dict`는 `.isoformat()`로 직렬화(이 셋만 `.isoformat()` 직접 호출 허용 — `id`의 `str(self.id)`와 동일), **`to_model`에선 제외**(쓰기는 DB가 `server_default`/soft-delete로 소유). fresh entity(`new()`/`with_*`)에선 `None`, DB-로드/RETURNING 결과에서만 채워짐

**enum 성격 VO는 허용값을 `_allowed_list` hint 속성으로 분리한다.** 고정된 허용 집합(`Role`, `Status`, `Source`, `ActorType` 등)을 가진 VO는 허용값을 팩토리 메서드 안 로컬 변수(`allowed = {...}`)나 inline 튜플로 두지 말고 클래스 레벨 `# hint` 필드로 선언. 검증은 `if value not in cls._allowed_list`.
- 타입: 튜플(`tuple[str, ...]`) — frozen dataclass는 mutable default(list/set/dict)를 못 받으므로 튜플 고정
- 허용값이 "데이터로서 선언"돼 한눈에 보이고, 테스트·문서화·재사용(예: API enum 노출) 시 `Role._allowed_list`로 접근 가능

**bool 플래그도 raw `bool`로 두지 않고 VO로 선언한다.** Entity의 `is_checked` 같은 플래그 필드는 `from_bool`/`to_bool`을 가진 VO로 승격 — 도메인 값은 전부 검증된 VO를 거친다는 원칙을 bool에도 일관 적용. `to_dict`/`to_model` 모두 `.to_bool()` 사용(DB가 Boolean 컬럼이라 표현이 안 갈림).
- 타입 가드는 `isinstance(value, bool)` — 파이썬에서 `isinstance(1, bool)`은 `False`라 int/str/None이 자동 차단된다
- 기본값이 필요하면 entity 필드는 required로 두고 `new(*, flag: IsChecked | None = None)`에서 `IsChecked.from_bool(False)`로 채운다 (VO는 mutable/factory 호출이라 dataclass 필드 기본값으로 부적절)
- repo finder가 DB 컬럼을 직접 조회할 때(`_filter_by(column="is_checked", value=False)`)는 원시 bool 그대로 — VO는 도메인 경계용, 쿼리 파라미터는 컬럼 타입에 맞춘다

**`UUID`는 VO로 만들지 않는다 — raw `UUID` 유지.** `id` / FK(`store_id`, `brand_id`, `actor_id` 등) / `request_id` / `idempotency_key`는 그냥 `uuid.UUID` 타입을 쓴다.
- 근거: `UUID`는 생성자가 형식을 보장하는 **이미 검증된 강타입**이라, email/datetime/bool 같은 stringly-typed/raw primitive와 성격이 다르다. `isinstance(x, UUID)` 가드는 동어반복이라 VO가 새 정보를 안 준다
- VO화의 유일한 실익은 "`store_id`에 `brand_id`를 잘못 넣는 혼동"을 타입으로 막는 것인데, 그러려면 FK마다 별도 타입(`StoreId`/`BrandId`)이 필요하고 → cross-aggregate import + `Entity.id` 타입 처리 등 복잡도가 이득을 상회한다고 판단해 보류
- 단일 공용 `Id` VO는 전부 같은 타입이라 혼동 방지 이득이 0 → 채택 안 함
- id 혼동은 타입이 아니라 리뷰/테스트로 커버한다

**freeform `dict`도 raw로 두지 않고 복합 VO로 감싼다.** `attributes`(order), `before`/`after`/`context`(audit_log) 같은 JSON 메타데이터도 `from_dict`/`to_dict` VO(`Address` 패턴)로 승격. raw `dict`는 frozen Entity의 불변성을 깨고(내부 변경 가능·unhashable) 컨벤션에서 벗어난다.
- `from_dict`/`to_dict`에서 `dict(value)`로 **방어적 복사** — 외부 참조로 내부 상태를 변형하지 못하게 한다

**정리 — Entity 필드에 raw primitive 금지.** 도메인 값(`str`/`int`/`bool`/`datetime`/`dict`)은 전부 VO로 승격한다. 예외는 둘뿐:
- `UUID` (id / FK / `request_id` / `idempotency_key`가 UUID인 경우) — 이미 강타입이라 유지
- `created_at` / `updated_at` / `deleted_at` — **read-only audit 필드로 `Entity` 베이스에 raw `datetime`** (write는 DB 소유, `to_model` 제외). `id`(raw `UUID`)와 같이 "베이스에 보이지 않게 존재"하는 프레임워크 필드 — 도메인 VO가 아니므로 raw 유지

식별 키성 str(`idempotency_key` 등)은 non-empty VO로 만들되, "선택적이고 유일"이면 모델은 `nullable=True` + partial unique index(`WHERE col IS NOT NULL`)로 — non-empty 가드만으론 막을 수 없는 "값 없는 다수 행"을 DB에서 허용하면서 값 있는 행만 유일성 강제. (예: `point_ledger.idempotency_key`)

**Entity 패턴**:

```python
@dataclass(frozen=True, kw_only=True)
class Brand(Entity):
    name: Name
    business_number: BusinessNumber | None = None
    
    @classmethod
    @typecheck
    def new(cls, *, name: Name, business_number: BusinessNumber | None = None) -> "Brand":
        return cls(name=name, business_number=business_number, by_factory=True)
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name.to_str(),
            "business_number": (
                self.business_number.to_str() if self.business_number else None
            ),
        }

    def to_model(self):
        return {
            "id": self.id,
            "name": self.name.to_str(),
            "business_number": (
                self.business_number.to_str() if self.business_number else None
            ),
        }
```

**Entity 원칙**:
- **Entity 상속 필수** → `by_factory=True` 가드, UUID id 자동
- **팩토리**: `@classmethod @typecheck def new(...)`
- **`to_dict()`**: API 응답용 (id 포함, UUID → str, datetime VO → `to_str()`)
- **`to_model()`**: DB 저장용 (**`"id": self.id` 반드시 포함** — model의 id 컬럼은 DB default가 없어 INSERT 시 필수. UUID/datetime은 native)
- **`with_X()`**: immutable evolve (필요시). 단순 필드 교체는 `with_value`처럼, **도메인 상태 전이**는 동사 메서드 허용 (예: `point_request.decide(*, status, decided_at, decided_by_type, decided_by_id, memo=None)` — 결정 필드 필수로 받아 부분 업데이트 데이터 유실 방지)

**변환 메서드 요약**:

| 방향 | ValueObject | Entity |
|------|-------------|--------|
| 입력 | `from_str` / `from_dict` / `from_datetime` / `from_bool` / `from_int` | `new` |
| 출력 | `to_str` / `to_dict` / `to_bool` / `to_int` (시간 VO는 `+ to_datetime`) | `to_dict`, `to_model` |

**Domain Event 패턴** — 마커는 **순수**(domain), 저장은 `EventRepository.emit`(event aggregate), 조정은 usecase.

```python
# domain/secret/secret_event.py — 순수 마커 (IO·다른 aggregate 의존 0)
@dataclass(frozen=True, kw_only=True)
class SecretEvent(Event):          # core/event.py Event 상속 (_id + id() 만 보유)
    _kind: SecretEventKind         # Enum, 값은 점 표기 "secret.created"
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

    def kind(self) -> str:          return self._kind.value
    def entity_type(self) -> str:   return "Secret"
    def entity_id(self) -> UUID:    return self.secret.id
    def to_dict(self) -> dict:      return {"kind": self._kind.value, "secret_id": str(self.secret.id)}
```

```python
# domain/event/event_repository.py — 마커 → Event entity 변환 후 일괄 저장
class EventRepository(PostgresRepository[Event, EventModel]):
    model = EventModel
    mapper = _to_event

    @classmethod
    async def emit(cls, *, session, events: list) -> list[Event]:
        return await cls.add_many(session=session, entities=[
            Event.new(id=e.id(), kind=Kind.from_str(e.kind()),
                      entity_type=EntityType.from_str(e.entity_type()), entity_id=e.entity_id())
            for e in events
        ])
```

```python
# usecase — 도메인 변경 + 마커 + 저장(emit) + 인라인 응답
event, entity = SecretEvent.created(
    secret=await SecretRepository.add(session=session, entity=Secret.new(...)),
)

return {
    "data": entity.to_dict(),
    "event": [e.to_dict() for e in (await EventRepository.emit(session=session, events=[event]))],
}
```

**Event 원칙**:
- 마커는 `core/event.py`의 `Event` 상속(`_id`+`id()`만) + `@dataclass(frozen=True, kw_only=True)`, **순수** — IO/async 없음, 다른 aggregate 의존 0. **id는 `created()` 시점 확정** → `Event.new(id=마커.id())`로 발행본·저장본 identity 일치
- `{Aggregate}EventKind(Enum)` — **값은 `{entity}.{eventname}` 점 표기**(`"secret.created"`). `to_dict`/`kind()`는 **`.value`**
- **명명 팩토리** `created`/`updated`/`deleted` — `@classmethod @typecheck`, **sync**, persist된 aggregate를 받음. **persist 호출을 감싸는 `created`/`deleted`는 `(마커, aggregate)` 튜플**(중첩 `add`/`remove_by_id` 결과를 `event, entity = ...` 한 줄로 풀기 위함), aggregate가 이미 손에 있는 `updated`는 단일 마커
- **접근자** `id()`/`kind()`/`entity_type()`/`entity_id()` — `EventRepository.emit`이 duck-typed로 읽어 `Event` entity로 변환
- 저장은 `EventRepository.emit`(event aggregate), 응답은 **인라인 dict**(`{"data": ..., "event": [...]}`) — 조정은 usecase 책임 (`Output` 래퍼 없음)

**Config 클래스**:
- `ABC` + `@property @abstractmethod` 인터페이스
- 프로퍼티명 = 환경변수 키와 동일한 UPPER_CASE
- 환경별 서브클래스 (`TestPostgresConfig` / `DevPostgresConfig` / `ProdPostgresConfig`)
- 모듈 수준 팩토리 함수 (`get_postgres_config()`) — Dev/Test/Prod 분기 때문에 factory 정당함

---

## Infrastructure 싱글톤

**모듈 수준 직접 인스턴스화.** factory 함수 wrapper 금지 — 호출 시 `()` 깜빡 버그 제거.

```python
# #
# Cafe24
cafe24 = Cafe24(config=get_cafe24_config())

# 호출
from franchise_manager.api.infrastructure.cafe24.client import cafe24
cafe24.method(...)
```

**섹션 마커는 PascalCase 클래스명** — "이 블록은 해당 클래스의 default 인스턴스"임을 표시. 일반 라벨(`# client`, `# cli` 등 lowercase 카테고리)의 예외 케이스.

여러 싱글톤이 같은 파일에 있으면 각각 별도 섹션:

```python
# #
# OAuthStateCache

oauth_state_cache = OAuthStateCache(config=get_cafe24_config())


# #
# OAuthTokenCache

oauth_token_cache = OAuthTokenCache(config=get_cafe24_config())
```

**factory 함수 wrapper는 금지** — 단, 예외:
- 환경별 인스턴스 선택 필요 (Config의 `get_postgres_config()` 같이 Dev/Test/Prod 분기)
- lazy 초기화 비용이 큰 인스턴스

```python
# ❌ 불필요한 wrapper
_cafe24 = Cafe24(...)

def cafe24() -> Cafe24:
    return _cafe24

# 호출: cafe24().method(...)  ← () 빠뜨리면 AttributeError silent
```

적용 예: `db_client`, `cafe24`, `oauth_state_cache`, `oauth_token_cache`.

**repository는 싱글톤이 아님** — classmethod 모음이라 인스턴스 없이 클래스 자체로 호출(`SecretRepository.add(...)`). 상세는 [python-architecture.md](./python-architecture.md) "패턴 1. Repository" + "패턴 4. Session = Transaction" 참고.

---

## UseCase 파일 구조

`usecase/{aggregate}/{action}.py` — Input + 함수 + CLI 3섹션.

```python
from __future__ import annotations
import argparse, asyncio
from pydantic import BaseModel
from franchise_manager.api.core.validate import typecheck
from franchise_manager.api.infrastructure.cafe24.client import cafe24
from franchise_manager.api.infrastructure.postgresql.client import db_client
from franchise_manager.api.infrastructure.postgresql.session import transactional_session

# #
# input
class Input(BaseModel):
    code: str

# #
# usecase
@typecheck
async def start_oauth(*, session, input: Input) -> Result:
    ...

# #
# cli
def _parse_args():
    return argparse.ArgumentParser().parse_args()
async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(await start_oauth(session=session, input=Input(code=args.code)))
if __name__ == "__main__":
    asyncio.run(_main())
```

### Input 모델

- **pydantic `BaseModel`** (도메인 ValueObject와 달리 `by_factory` 가드 없음 — Input은 boundary 입력 검증용, 도메인 객체 아님)
- 입력 필드 없어도 **항상 정의**: `class Input(BaseModel): pass`. 호출 시그니처를 일관되게 유지 (`input=Input()`).
- 클래스명은 `Input` 고정 — 파일명(`{action}`)이 컨텍스트 제공 → 폴더/파일 컨텍스트 중복 금지 규칙 따름

### usecase 함수 시그니처

```python
@typecheck
async def {action}(*, session, input: Input) -> Result:
```

- `@typecheck` 필수
- **kwarg-only** (`*` 강제) — session/input 순서 고정
- `session = AsyncSession`(트랜잭션 경계), `input = Input 인스턴스`만 받는다 — repo는 클래스로, 인프라 싱글톤(`session_cache` 등)은 모듈 import로 직접 접근하므로 db 핸들을 인자로 받지 않는다
- repository는 **클래스로 import** — `from ... import SecretRepository`. 호출 시 `SecretRepository.add(session=session, ...)` (인스턴스화 X)
- 외부 시스템 싱글톤(`cafe24`, `oauth_*_cache`)은 모듈 import로 직접 참조
- sync/async는 IO 유무에 따라 — 순수 in-memory 조작뿐이면 sync 가능 (`start_oauth`는 sync, `complete_oauth`는 async)

### 본문 내 컨벤션

- 단계별 `# label` 인라인 마커: `# state`, `# exchange`, `# persist`, `# cache` 등
- persistence helper(`_upsert` 같은 거) 함수 안에 두지 말 것 — domain repo의 메서드(`set_by_key`)로 끌어올림 → [python-architecture.md](./python-architecture.md) 의사결정 체크리스트 참고

### CLI 섹션

- `_parse_args` — argparse, input 모델 필드와 1:1 매핑되는 `--flag` 추가
- `_main` — **항상 async** (session이 async라서). usecase가 sync여도 `_main`은 async + `async with transactional_session(...)`로 session 열기
- 결과 출력: usecase가 의미 있는 값 반환하면 `print(result)`, `None` 반환이면 생략 가능 (현 lab은 일관성 위해 `print(await ...)` 사용 — `None`이 찍혀도 무방)
- `# cli` 섹션 내부는 함수 사이 빈 줄 1줄 (파일 구조 섹션 참고)

### 실제 예시

- [usecase/cafe24/start_oauth.py](../../franchise_manager/api/usecase/cafe24/start_oauth.py) — 입력 없음 (`Input(BaseModel): pass`) + sync 함수
- [usecase/cafe24/complete_oauth.py](../../franchise_manager/api/usecase/cafe24/complete_oauth.py) — 입력 있음 (`code`, `state`) + async 함수 + 다중 저장소 갱신

---

## Import

순서: 표준 → 서드파티 → 로컬. 그룹마다 한 줄 공백. 로컬은 `from api.xxx` (패키지 루트 `worship_support` 생략). 도메인 클래스는 **한 줄에 하나씩** 별도 import.

```python
import re
from dataclasses import dataclass

from api.core.value_object import ValueObject

from api.domain.user.name import Name
from api.domain.user.birth import Birth
from api.domain.user.email import Email
```

### 라우터/registry — 모듈 namespace import

여러 핸들러를 한 모듈에서 등록할 때는 **`from package import module`** 형태로 import하고 `module.func`로 접근. alias 노이즈 제거 + namespace 의도 명확.

```python
# ✓ 모듈 namespace — 한 모듈에서 N개 함수 등록
from franchise_manager.api.endpoint import cafe24

server.router(Router(path="/auth/cafe24/start",    methods=["GET"], endpoint=cafe24.start))
server.router(Router(path="/auth/cafe24/callback", methods=["GET"], endpoint=cafe24.callback))
```

```python
# ❌ alias 패턴 — endpoint 추가마다 import 늘어남
from franchise_manager.api.endpoint.cafe24 import start as cafe24_start
from franchise_manager.api.endpoint.cafe24 import callback as cafe24_callback
```

**적용 기준**:
- 한 모듈에서 **2개 이상** 함수 import → 모듈 namespace (`from pkg import mod`)
- 한 모듈에서 **1개**만 import → 함수 직접 (`from pkg.mod import func`)

적용 위치 예: FastAPI router 등록 (`bin/server.py`), CLI dispatcher, MCP tool registry 등 "여러 핸들러를 외부 시스템에 등록"하는 파일.

도메인/usecase/repository 호출처에는 적용 안 함 — 그쪽은 도메인 클래스 한 줄당 import 규칙 그대로.

---

## 비동기

- DB 접근 메서드는 `async`
- 트랜잭션은 `@asynccontextmanager` 헬퍼로 래핑
- 추상 비동기 메서드 본문도 `...`

```python
@asynccontextmanager
async def transactional_session(session_factory):
    session = session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
```

---

## 포맷팅

- 들여쓰기 4칸
- import 블록 후 두 줄 공백
- 모듈 함수 사이 두 줄 공백 (`# cli` 섹션 내부는 한 줄 예외 — 파일 구조 섹션 참고)
- 메서드 사이 한 줄 공백
- 긴 함수 시그니처: 파라미터마다 줄바꿈 + trailing comma
- `if __name__ == "__main__":` 는 파일 하단 `# cli` 또는 `# run` 섹션

**flat dict return의 삼항식은 괄호로 감싸 줄바꿈.** `to_dict` / `to_model`처럼 한 줄 = 한 키인 평평한 딕셔너리에서, 값에 `... if ... else ...`가 들어가면 키 라인이 길어져 한눈에 안 들어온다. 괄호 + 줄바꿈으로 "이 키는 예외적 분기가 있다"를 시각적으로 분리한다.

```python
# ❌ 한 줄에 삼항식
return {
    "business_number": self.business_number.to_str() if self.business_number else None,
}

# ✓ 괄호 + 줄바꿈
return {
    "business_number": (
        self.business_number.to_str() if self.business_number else None
    ),
}
```

- 단순 값(`"name": self.name.to_str()`)은 한 줄 유지 — 삼항식 등 분기 문법이 있을 때만 적용
- 닫는 괄호 `)` 다음 trailing comma 유지

---

## 주석 언어

- 코드 라벨/섹션 마커: **영어** (`# factory`, `# query`)
- 도메인 의미가 강한 docstring (MCP tool 설명 등): **한국어 허용**

---

## 핵심 철학

> **DDD 레이어 분리 + 팩토리 강제 + 시각적 섹션 마커(`# #`) + 자명한 파일 구조**

코드의 의도가 라벨 주석과 파일 구조로 시각적으로 드러난다. 도메인 객체는 검증된 팩토리로만 생성. 단일 파일은 호출 순서 = 읽기 순서로 배치되어 파일을 열었을 때 1초 안에 의도가 파악되어야 한다.