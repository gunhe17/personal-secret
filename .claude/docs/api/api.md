# api 문서 — `personal_secret/api/`

DDD 아키텍처 + 코드 컨벤션의 **루트 라우터**. 이 문서만 always-on — 나머지(`conventions.md` + `reference/` + `recipe/`)는 **편집 직전 JIT Read**. 역할은 둘: ① 올바른 문서로 **라우팅** ② 절대 규칙 **불변식(INV)** 을 한 곳에 박아두기.

> 철학: DDD 레이어 분리 + 팩토리 강제 + `# #` 섹션 마커 + 자명한 파일 구조.
> 문서는 **코드 폴더가 아니라 패턴 단위**로 조직된다(`reference/repository.md`는 core·infra·domain의 repository 조각을 한 곳에). 코드 경로 → 문서는 추론하지 말고 아래 표에서 조회한다.

## 항해 규칙

작업은 셋 중 하나의 질문으로 들어온다 — 질문 유형이 진입점이다:

- **WHERE** (어디 두지) → 아래 [의사결정 체크리스트](#의사결정-체크리스트) + 의존 방향
- **WHAT-RULE** (규칙이 뭐지) → 아래 [라우팅 표](#라우팅--무엇을-만지면-무엇을-읽나)로 `reference/` 문서 Read
- **HOW-TO** (이 작업 어떻게) → 아래 [작업별 recipe](#작업별-recipe-how-to)
- **HOW-NOT** (어기면 안 되는 것) → 아래 [불변식 INV](#불변식-inv)

철칙: **코드 만지기 전 해당 `reference/` 문서 Read**(반환 규약·예외 메시지·이벤트 마커 등 세부는 거기에만). **모든 `.py`는 [conventions.md](conventions.md) 먼저.**

## 라우팅 — 무엇을 만지면 무엇을 읽나

의존: `bin → server → endpoint → usecase → domain → infrastructure` (위→아래 import만, 모두 →`core`) — **[INV-1]**. 완화: `domain/{agg}/{agg}_repository.py`가 SQLAlchemy `Model` 동거 + `PostgresRepository`(infra) 상속.

| 만지는 것 (glob) | 읽을 문서 (`reference/`) |
|---|---|
| 모든 `.py` | [conventions.md](conventions.md) (항상 먼저) |
| `domain/*/{value}.py` · `core/value_object.py` | [reference/value-object.md](reference/value-object.md) |
| `domain/*/{agg}.py` · `core/entity.py` | [reference/entity.md](reference/entity.md) |
| `domain/*/{agg}_repository.py` · `infrastructure/postgresql/repository.py` · `core/repository.py` · `core/model.py` | [reference/repository.md](reference/repository.md) |
| `domain/*/{agg}_event.py` · `domain/event/**` · `core/event.py` | [reference/domain-event.md](reference/domain-event.md) |
| `usecase/**` · `core/usecase.py` | [reference/usecase-flow.md](reference/usecase-flow.md) |
| `endpoint/**` | [reference/endpoint.md](reference/endpoint.md) |
| `bin/server.py` · `server/**` | [reference/server.md](reference/server.md) |
| `infrastructure/crypto/**` · `postgresql/client.py` · `config.py` | [reference/singleton-config.md](reference/singleton-config.md) |
| `*/exception.py` · `core/exception.py` (예외 추가/이동) | [reference/exception.md](reference/exception.md) (예외 단일 권위) |
| `core/validate.py` (`@typecheck`) | [conventions.md](conventions.md) |

## 작업별 recipe (HOW-TO)

여러 문서를 순서대로 거치는 작업은 recipe가 절차를 시퀀싱한다(규칙 본문은 `reference/`, recipe는 순서만):

| 작업 | recipe |
|---|---|
| 새 aggregate 전체(도메인→API) | [recipe/add-aggregate.md](recipe/add-aggregate.md) |
| usecase 동작 추가 | [recipe/add-usecase.md](recipe/add-usecase.md) |
| ValueObject 추가 | [recipe/add-value-object.md](recipe/add-value-object.md) |
| 예외 추가/이동 | [recipe/add-exception.md](recipe/add-exception.md) |

## 불변식 (INV)

패턴을 가로지르는 절대 규칙 — **여기가 단일 권위**. `reference/`는 재서술 없이 `[INV-N]`으로 참조. 위반은 `INV-N`으로 인용.

- **[INV-1] 의존 방향** — 위→아래 import만, 모두 →`core` (완화 예외는 위 라우팅).
- **[INV-2] 팩토리 강제** — Entity/VO는 `new`/`from_*`로만 생성, `by_factory` 가드로 직접 생성 차단.
- **[INV-3] base write 계약** — base 단건 fetch/write(`find_by_id`/`update`/`remove_by_id`)는 `E | None`, business 예외 raise 안 함. must-exist면 domain이 override해 `None → NotFoundError`로 좁힘(`update`/`remove_by_id` 대칭).
- **[INV-4] 예외 귀결** — 모든 예외는 레이어 `common/exception.py`(또는 dialect `postgresql/exception.py`)→레이어 베이스→`ClientError`(4xx)/`DevelopError`(5xx). `core/exception.py`는 루트 전용.
- **[INV-5] session = transaction** — usecase 1개 = 1 트랜잭션, 모든 repo 호출에 같은 `session=` 주입. usecase 내부 `commit()`/`begin()` 금지.
- **[INV-6] repo는 stateless classmethod** — 인스턴스화/싱글톤 금지, 클래스로 호출, session은 메서드 인자.
- **[INV-7] 이벤트 마커는 순수** — IO/async·타 aggregate 의존 0. 저장은 `EventRepository.emit`, 조정은 usecase.
- **[INV-8] 응답은 인라인 dict** — `{"data": ..., "event": [...]}`, `Output` 래퍼 없음.
- **[INV-9] unique 2계층** — base `_ensure_unique`(`UniqueViolationError`) + domain 변환(`AlreadyExistsError`). usecase는 `{action}_unique_by_{col}` 호출만.
- **[INV-10] raw primitive 금지** — 도메인 값(str/int/bool/datetime/dict)은 VO로. 예외는 `UUID` id/FK + audit datetime뿐.

## 의사결정 체크리스트 (WHERE — 어디에 둘지)

1. **동작이 entity 1개에만?** YES → domain repo 메서드 / NO → `PostgresRepository`(infra)로 끌어올림 (+ `with_X`/`new(*, key, value)` 컨벤션).
2. **helper가 흐름 조립 vs 도메인 동작?** 조립 → usecase 인라인/`_helper` / 도메인 동작 → domain repo·entity 메서드.
3. **싱글톤이 환경 분기 필요?** YES → factory(`get_postgres_config()`) / NO → 직접 모듈 변수(`db_client = ...`).
4. **import 방향?** → **[INV-1]**.
5. **새 파일 만들기 전 동거 가능?** domain repo는 중간 파일 없이 `domain/{agg}/{agg}_repository.py`에, 싱글톤 여럿도 한 파일에.
