---
paths:
  - "personal_secret/api/**/*_repository.py"
  - "personal_secret/api/infrastructure/database/postgresql/repository.py"
  - "personal_secret/api/infrastructure/database/common/repository.py"
  - "personal_secret/api/core/model.py"
---

# Repository 패턴

영속화 — 세 조각이 한 곳에: core의 추상 계약(`Repository[T]`), infrastructure의 일반화 부모(`PostgresRepository`), domain의 wiring(`{Aggregate}Repository`). SQLAlchemy `Model`은 domain repo 파일에 동거([INV-1] 완화).

루트: [api/CLAUDE.md](../../../personal_secret/api/CLAUDE.md) · entity: [entity.md](entity.md) · 예외: [exception.md](exception.md)

---

## 이 문서

| 섹션 | 핵심 규칙 |
|------|----------|
| **계층** | 추상 `Repository[T]`(core) → concrete `PostgresRepository`(infra) → wiring `{Aggregate}Repository`(domain) |
| **호출 규약** | stateless classmethod, 인스턴스화 금지, session은 메서드 인자 — **[INV-6]** |
| **write 계약** | base 단건 fetch/write는 `E \| None`, business 예외 raise 안 함. must-exist는 domain override — **[INV-3]** |
| **query** | `_filter(where=[clause])` + `deleted_at IS NULL` 자동. 파이썬 후필터 금지 |
| **unique** | base `_ensure_unique`(`UniqueViolationError`) + domain 변환(`AlreadyExistsError`) 2계층 — **[INV-9]** |
| **KV** | `set_by_key` upsert는 domain에 직접(aggregate 1개라 일반화 안 함) |

---

## 계층 — 추상 / 일반화 / wiring

```
infrastructure/database/
  common/repository.py        Repository[T]            추상 classmethod (add/find_by_id/update/remove_by_id), 반환 E|None
  postgresql/repository.py    PostgresRepository[T,M]  query/CRUD 일반화 concrete 부모
domain/{agg}/{agg}_repository.py
                              {Aggregate}Repository    Model 동거 + class vars(model/mapper) + 커스텀 finder wiring
```

- 추상 계약(database/common): 단건 fetch/write 반환은 nullable(`Any | None`) — base는 business 예외 raise 안 함 ([INV-3])
- 일반화 부모(infra): 도메인이 2개 이상 entity에 같은 패턴을 반복하면 여기로 끌어올린다. 중간 파일(`infrastructure/database/postgresql/{agg}_repository.py`) 금지 — domain repo가 `PostgresRepository`를 직접 상속
- wiring(domain): class variables(`model`/`mapper`)만 정의하면 base classmethod가 `cls.model`/`cls.mapper`로 동작(`__init__`/`__init_subclass__` 없음). 일반화 안 된 도메인 동작만 `@classmethod`로 직접 구현

---

## 호출 규약 — stateless classmethod — [INV-6]

인스턴스/싱글톤 없이 클래스 자체로 호출. session은 모든 메서드의 `session=` kwarg(= transaction 경계, [usecase-flow.md](usecase-flow.md)).

```python
# (a) 순수 wiring
class VaultRepository(PostgresRepository[Vault, VaultModel]):
    model = VaultModel
    mapper = _to_vault

# (b) 커스텀 finder (1줄 delegation)
class SecretRepository(PostgresRepository[Secret, SecretModel]):
    model = SecretModel
    mapper = _to_secret

    @classmethod
    async def find_by_name(cls, *, session, name: Name) -> Secret | None:
        return await cls._find_by(session=session, column="name", value=name.to_str())
```

```python
# 호출 — 클래스 자체로
secret = await SecretRepository.add(session=session, entity=Secret.new(...))
found  = await SecretRepository.find_by_name(session=session, name=name)
```

- 제네릭이 타입 좁힘: `PostgresRepository[Secret, SecretModel]`라 `.add(...)` 반환은 이미 `Secret`. passthrough override 불필요
- `mapper` 바인딩: `mapper = _to_secret`은 `cls.mapper(model)` 언바운드 호출 — `self` 안 끼어 classmethod에서 안전

---

## CRUD + query 코어 (부모 제공)

- CRUD: 생성 `add`/`add_many`, 조회 public `find_by_id`/`find_by_ids`/`exists_by_id`/`list_all`, 수정 `update`/`update_many`, 삭제 `remove_by_id`
- query 코어 protected: `_filter`/`_find`/`_count`/`_page` + sugar `_find_by`/`_filter_by`/`_filter_by_all`/`_exists_by`, guard `_ensure_unique`
- `_filter(*, where=[clauses], order_by, descending, limit, offset)` — `where` = SQLAlchemy boolean clause 리스트(전부 AND, `deleted_at IS NULL` 자동). plumbing(정렬/페이지/매핑/RETURNING)은 코어 소유 → 연산자 추가 시 코어 시그니처 불변

복합 쿼리 — clause 리스트: 여러 조건/연산자/OR은 모델 컬럼으로 clause를 만들어 `_filter(where=[...])`에 넘긴다:

```python
@classmethod
async def search(cls, *, session, kind=None, tag=None, query=None) -> list[Secret]:
    where = []
    if kind is not None:  where.append(SecretModel.kind == kind.to_str())
    if tag is not None:   where.append(SecretModel.tags.contains([tag]))   # JSONB @>
    if query is not None: where.append(SecretModel.name.ilike(f"%{query}%"))
    return await cls._filter(session=session, where=where, order_by="name")

# OR/중첩도 SQLAlchemy 그대로
where = [sa.or_(SecretModel.name.ilike(f"%{q}%"), SecretModel.tags.contains([q]))]
```

> SQLAlchemy `Model`(`core/model.py`의 `Base` 상속)은 domain repo 파일에 동거(`SecretModel`/`SecretRepository`). mapper 함수(`_to_secret`)는 모듈 중간, 모듈 끝에 싱글톤 두지 않음.

---

## write 반환 규약 + must-exist override — [INV-3]

write 메서드는 DB 반영 entity를 반환(`add -> E`, `add_many -> list[E]`, `update -> E | None`, `remove_by_id -> E | None`):

- `add`는 `flush` 후 server_default(`created_at`/`updated_at`) 채워진 model을 매퍼 변환해 반환
- `update`/`remove_by_id`는 `... RETURNING <model>`로 갱신/soft-delete 행을 한 문장에 받음(soft-delete 행은 `deleted_at IS NULL` 필터에 걸려 재조회 안 됨 → RETURNING이 정답)
- base는 `.first()`+`None`(`E | None`, raise 안 함) — 부재가 비정상인 **must-exist**면 domain repo가 `update`/`remove_by_id`를 override해 `None → NotFoundError`로 raise(반환을 `E`로 좁힘). `update`/`remove_by_id` 완전 대칭, "본문 있는 도메인 가드"라 passthrough-override 예외
  - 적용 조건: ① must-exist 의미일 때만(optional/멱등 upsert면 base 그대로, usecase가 `None` 분기) ② 본문 없는 단순 위임 금지 ③ base 계약(`E | None`)을 좁히므로 `None` 기대 호출처 없어야 함(끌어올리기 전 의존처 확인)
  - 효과: not-found 변환의 단일 발생처 = repo. usecase는 happy-path만

usecase는 반환 entity를 `to_dict()` — 생성/수정 응답에도 타임스탬프 일관. exists는 의도대로 `bool` 유지.

---

## unique 강제 — 2계층 — [INV-9]

유일성은 base 사전검사 guard + 도메인 변환의 2계층. domain repo가 `{action}_unique_by_{col}`로 노출한다.

- base `_ensure_unique(*, session, entity, unique: list[str | tuple], exclude_id=None) -> None`: `unique`의 각 원소 = 제약 1개 — `str`은 단일 컬럼, `tuple`은 복합(그룹 내 컬럼 AND). 제약마다 `_count` 검사, 있으면 infra `UniqueViolationError`(`database/common/exception.py`, 409) raise. update 자기 행은 `exclude_id`로 제외. `deleted_at IS NULL` 자동(soft-delete된 이름 재사용 허용, partial unique index와 일치)
- domain 변환: `try/except`로 `UniqueViolationError`(infra) → `AlreadyExistsError`(domain). base는 도메인 예외를 모른다
- 메서드명에 유일 컬럼 명시(`add_unique_by_name`/`update_unique_by_name`), 복합키는 tuple로 묶는다 — `add_unique_by_name_and_kind` + `unique=[("name", "kind")]` (`["name", "kind"]`는 두 컬럼을 *각각* 검사하는 OR이라 복합 아님)
- write는 `_ensure_unique` 밖에서 호출 — `cls.add`는 `-> E`, `cls.update`는 도메인 must-exist override라 `-> E`. update는 `exclude_id=entity.id`로 자기 행 제외
- 경합은 안 잡는다 — 무결성 단일 출처는 테이블 partial unique index, guard는 1차 방어(흔한 충돌에 깔끔한 메시지). 뚫은 동시 삽입은 raw `IntegrityError` → 500

```python
@classmethod
async def add_unique_by_name(cls, *, session, entity: Secret) -> Secret:
    try:
        await cls._ensure_unique(session=session, entity=entity, unique=["name"])
    except UniqueViolationError:
        raise AlreadyExistsError("Secret", entity.name.to_str())
    return await cls.add(session=session, entity=entity)
```

---

## KV 패턴

`setting` aggregate가 실례. entity `.new(*, key, value)` + `.with_value(value)`, model `key` 컬럼(active partial unique index) + `value` JSONB. `set_by_key`(upsert)는 domain repo에 직접 — `find_by_key` → 있으면 base `update`, 없으면 base `add`. upsert라 충돌 reject 안 하므로 `_ensure_unique` 안 씀(중복 키는 갱신). KV aggregate가 1개뿐이라 base로 끌어올리지 않는다(위 "일반화 부모": 2개 이상일 때 일반화). 2번째 KV 생기면 `set_by_key`(+배치 `set_by_keys`)를 `PostgresRepository`로 일반화.

---

## 부모 vs 자식 판정

- entity 1개에만 쓰이고 일반화 어려움 → domain repository classmethod로
- 2개 이상 entity에 패턴 반복 → `PostgresRepository`로 끌어올리기 + entity 컨벤션(`with_X`/`new(*, key, value)`) 합의

---

## 안티패턴

- domain repo가 `select(...).where(...)` 문 전체 작성(plumbing 재구현) → 코어 위임. 단 `Model.col == v` clause를 `_filter(where=[...])`에 넘기는 건 정석
- fetch 후 파이썬 후필터/정렬/슬라이싱(`[x for x in ...]`, `sorted`, `[:n]`) → `_filter(where=[...])` + `order_by` + `limit`/`offset`(페이지는 `_page`)
- 존재 확인을 `find_by_X(...) is not None`(entity 전체 fetch) → `exists_by_X`(`_exists_by`, count 기반 `bool`)
- domain repo `__init__`/`__init_subclass__` → `model`/`mapper` class variable만
- domain repo 메서드를 인스턴스 메서드(`self`)로 / repo 싱글톤·인스턴스화 → 전부 `@classmethod`, 클래스 자체 호출 ([INV-6])
- base CRUD passthrough override(`async def add(...): return await super().add(...)`) → 제네릭이 타입 좁힘. 본문 있는 도메인 가드일 때만 override
- `infrastructure/database/postgresql/{agg}_repository.py` 중간 파일 → domain repo가 `PostgresRepository` 직접 상속
- unique 충돌을 usecase에서 검사·raise → domain `{action}_unique_by_{col}` ([INV-9])
