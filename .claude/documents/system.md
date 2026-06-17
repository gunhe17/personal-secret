# 공유 프로젝트 규칙

전 레이어 공통 — MCP 의존성 조회 + 수정 워크플로우. CLAUDE.md가 `@`로 직접 로드.

---

## MCP

- 역참조(누가 나를 쓰나, dependents): `mcp__personal-secret-dev__show_dependents`
- 방향검사(내가 무엇에 의존하나 — INV-1, dependencies): `mcp__personal-secret-dev__show_dependencies`

## 수정 워크플로우

1. `show_dependents`로 의존처(사용처) 확인
    1-2. if, MCP 결과 `no usages` / `no definitions`라면 그 결과를 신뢰한다. Grep·Glob으로 재검증하지 않는다. MCP 서버 응답 불가일 때만 대체 수단 사용.
2. 대상 수정
3. 의존처 전부 반영