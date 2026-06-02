# api

암호화 시크릿 저장소 백엔드 (FastAPI + PostgreSQL).

도커 컨테이너에서 `127.0.0.1` 전용으로 동작하며 웹 UI(`/`)와 REST API를 제공한다.
`cli`(호스트)와 브라우저 양쪽에서 호출한다.

## 레이어

`endpoint → usecase → domain → infrastructure → core` (DDD 5계층, 위→아래 단방향 의존).

- **domain/vault** — 마스터 키 봉투(`salt`, `wrapped_dek`). 단일 행 집합체.
- **domain/secret** — 시크릿(`kind`, `name`, `tags`, `expires_at`, `ciphertext`). 본문은 암호화.
- **infrastructure/crypto** — Argon2id KDF + AES-256-GCM(`client.py`) + unlock 세션(`cache.py`).
