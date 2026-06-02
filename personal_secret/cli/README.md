# cli

호스트(macOS)에서 도는 `secret` 명령. 컨테이너의 `api`와 `127.0.0.1` HTTP로 통신한다.

키체인·Touch ID·`ssh` 실행은 호스트 전용 기능이라 컨테이너가 아닌 호스트에서 실행한다.

- **infrastructure/api** — api 컨테이너 HTTP 클라이언트.
- **infrastructure/keychain** — macOS 키체인(마스터 비밀번호) + LocalAuthentication(Touch ID).
- **infrastructure/ssh** — 저장된 ssh 시크릿으로 `ssh` 프로세스 구성·실행.
- **command/** — `init`/`unlock`/`lock`/`status` · `add`/`ls`/`get`/`rm`/`ssh`/`expiring`.

설치는 루트 [README](../../README.md) 참고.
