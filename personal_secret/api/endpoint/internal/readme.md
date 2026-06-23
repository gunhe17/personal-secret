# endpoint/internal

내부 이벤트(NOTIFY)로 트리거되는 핸들러 — HTTP endpoint(`../`)의 worker 짝.

- **무엇**: worker(`Work`)가 채널 NOTIFY를 받아 디스패치하는 진입점. 외부 주소·HTTP 응답 없음(fire-and-forget).
- **왜 endpoint이되 internal**: 라우터가 디스패치하는 진입점이라 endpoint, 단 트리거가 외부 요청이 아니라 내부 이벤트(push)라 `internal/`로 가른다.
- **역할**: payload 파싱 + business(usecase)를 worker UoW(`behavior/worker.py`)에 바인딩만. action·비즈니스 로직은 아래 레이어가 — 얇게.
- **등록**: `bin/worker.py`의 `Work`.

패턴/규칙: `.claude/rules/api/endpoint-internal.md`
