---
description: 기존 aggregate에 usecase 동작 하나(create/update/reveal/list/delete 등)를 추가할 때. Input + 함수 + CLI 3섹션 절차.
---

# Recipe: UseCase 추가

aggregate에 동작 하나(`create`/`update`/`reveal`...) 추가. 규칙 본문은 [reference/usecase-flow.md](../../../../../.claude/rules/api/usecase-flow.md).

선행: [conventions.md](../../../../../.claude/rules/shared/conventions.md) 1회 + [reference/repository.md](../../../../../.claude/rules/api/repository.md)(repo 호출).

## 절차

1. 파일 — `usecase/{aggregate}_{action}.py` (폴더 없이 평탄, `# input` / `# usecase` / `# cli` 3섹션)
2. Input — `class Input(BaseModel)` (필드 없어도 정의). pydantic, `by_factory` 가드 없음
3. 함수 — `@typecheck async def {action}(*, session, input: Input) -> Result`
4. 본문 라벨 — `# find`(조회) → `# {동작}`(파일명 동사) → `# persist`(쓰기 있으면) → `# return`
   - repo는 클래스로 호출, 모든 호출에 `session=session` (**[INV-5]**, [reference/repository.md](../../../../../.claude/rules/api/repository.md))
   - 인프라 싱글톤(`argon2`/`token` 등)은 모듈 import 직접
   - must-exist 조회는 repo `get_*`(없으면 raise), unique 쓰기는 `{action}_unique_by_{col}`
5. 이벤트(쓰기면) — 마커 생성 + `EventRepository.emit(session=session, events=[...])`, 인라인 dict 응답 ([reference/domain-event.md](../../../../../.claude/rules/api/domain-event.md))
6. CLI — `_parse_args`(input 필드 1:1 `--flag`) → `_main`(async, `async with transactional_session`) → `if __name__`
7. 노출 — endpoint 핸들러 추가([recipe/add-aggregate](../add-aggregate/SKILL.md) 6~7단계 참고) 또는 CLI만

## 체크

- [ ] 응답이 인라인 dict인가 — `Output` 래퍼 없음 ([INV-8])
- [ ] `if x is None: raise` 가드를 usecase에 안 뒀나 → repo override ([INV-3])
- [ ] persistence helper(`_upsert`)를 usecase에 안 뒀나 → repo로
- [ ] usecase 내부 `commit()`/`begin()` 없나 ([INV-5])
