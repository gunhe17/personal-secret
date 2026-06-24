# 불변식(INV) 레지스트리 + 레이어 방향

`[INV-N]` 인용의 단일 해소처. 한 줄 정의는 여기가 권위, 패턴·강제는 확장 문서가 소유(중복 금지).

---

## 레이어 의존 방향 — [INV-1] (여기서 정의)

의존은 한 방향 — 하위만 의존하고 상위는 모른다. 어댑터(`server/`·`worker/`)는 도메인 무지(`Callable`만).

    bin/  →  server/ worker/  →  endpoint/(internal/)  →  behavior/
      →  usecase/  →  { domain/ , infrastructure/ }  →  core/  ·  config.py

- 왼→오 방향으로만 import. 역방향(`domain`이 `usecase`를, `core`가 무엇이든) 금지.
- `core/`는 아무것도 import 안 함(의존 0). `domain/` ⊥ `infrastructure/` — 서로 모른다(usecase가 주입).
- 검사: `mcp__personal-secret-dev__show_dependencies` + `hint_dependencies.py` 훅 (system.md).

---

## INV 레지스트리

| INV | 한 줄 정의 | 확장 |
|---|---|---|
| INV-1 | 레이어 의존 방향 — 하위만 의존, 상위 모름 | (위) |
| INV-2 | VO = frozen dataclass + `by_factory` 팩토리 강제 | value-object.md |
| INV-3 | must-exist 조회는 repo가 `None→raise`, usecase 가드 금지 | repository.md |
| INV-4 | 모든 예외는 `ClientError`/`DevelopError`로 귀결 | exception.md |
| INV-5 | 같은 session=transaction, usecase 1개=1 트랜잭션 | usecase-flow.md |
| INV-6 | repository는 stateless classmethod (인스턴스화 안 함) | repository.md |
| INV-7 | 도메인 이벤트 atomic은 순수 (자기 aggregate만, IO 0) | domain-event.md |
| INV-8 | usecase는 항상 `Output(data, event)` 반환 | usecase-flow.md |
| INV-9 | unique 충돌은 domain repo가 강제 (usecase 사전검사 금지) | usecase-flow.md |
| INV-10 | 도메인 값은 전부 VO (예외: UUID id/FK·audit datetime) | value-object.md |
