---
paths:
  - "personal_secret/api/infrastructure/crypto/**"
  - "personal_secret/api/infrastructure/postgresql/client.py"
  - "personal_secret/api/config.py"
---

# 싱글톤 + Config 패턴

외부 시스템 어댑터 인스턴스(`db_client`/`crypto`)와 환경별 설정. `infrastructure/` + `config.py`에 산다.

루트: [api/CLAUDE.md](../../../personal_secret/api/CLAUDE.md) · repo: [repository.md](repository.md)

---

## 이 문서

| 섹션 | 핵심 규칙 |
|------|----------|
| **싱글톤** | 모듈 수준 직접 인스턴스화. factory wrapper 금지(환경분기·lazy만 예외) |
| **섹션 마커** | PascalCase 클래스명(`# Crypto`) — "이 블록은 default 인스턴스" |
| **Config** | `ABC` + 환경별 서브클래스 + `get_*_config()` 팩토리, `api/config.py`에 위치 |
| **crypto 경계** | 서버 crypto = 인증 해시 + 토큰뿐. 시크릿/키 암복호는 클라(E2EE) |

---

## 싱글톤 — 모듈 수준 직접 인스턴스화

factory 함수 wrapper 금지 — 호출 시 `()` 깜빡 버그 제거.

```python
# infrastructure/postgresql/client.py
# #
# Postgres
db_client = Postgres(get_postgres_config().database_url())

# infrastructure/crypto/client.py
# #
# Crypto
crypto = Crypto()
```

```python
# 호출
from personal_secret.api.infrastructure.postgresql.client import db_client
db_client.method(...)
```

- 섹션 마커는 PascalCase 클래스명 — "이 블록은 해당 클래스의 default 인스턴스"(일반 lowercase 라벨의 예외). 여러 싱글톤은 각각 별도 섹션
- factory 함수 wrapper 금지 — 예외: ① 환경별 인스턴스 선택(Config) ② lazy 초기화 비용 큰 인스턴스

```python
# bad: 불필요한 wrapper — 호출 시 () 빠뜨리면 AttributeError silent
_crypto = Crypto(...)
def crypto() -> Crypto:
    return _crypto
```

> repository는 싱글톤이 아님 — classmethod 모음이라 인스턴스 없이 클래스 자체로 호출 (**[INV-6]**, [repository.md](repository.md)).

---

## Config 클래스

모듈 수준 상수 블록(`MAX_X = ...`) 대신 환경별 분기를 캡슐화.

- 위치: `personal_secret/api/config.py` — config는 `infrastructure/` 하위가 아니라 api 루트(여러 infra 어댑터가 공유)
- `ABC` + `@property @abstractmethod` 인터페이스 (`PostgresConfig(ABC)`)
- 프로퍼티명 = 환경변수 키와 동일한 UPPER_CASE
- 환경별 서브클래스 (`TestPostgresConfig`/`DevelopPostgresConfig`/`ProductionPostgresConfig`)
- 모듈 수준 팩토리 (`get_postgres_config()`) — Develop/Test/Production 분기라 factory 정당

---

## crypto 경계 — 서버는 평문/키를 안 본다 (E2EE)

서버 `crypto`는 **인증 해시 + 토큰**만 담당한다. 시크릿·팀키의 암복호는 전부 클라가 하고, 서버는 평문도 평문키도 어떤 시점에도 보유하지 않는다.

- `crypto`(`crypto/client.py`)가 소유하는 것뿐: `hash_password`/`verify_password`(Argon2), `generate_token`/`hash_token`(SHA-256)
- 시크릿 `value`는 **클라가 team_key로 암호화한 ciphertext(base64)** — 서버는 `Ciphertext.from_str(...)`로 받아 그대로 저장, 복호화 안 함
- 도메인은 blob을 단일 VO(`Ciphertext`)로 감쌀 뿐 — 내부 포맷(nonce/AEAD)은 클라 소유라 서버가 모름
- 서버측 DEK 캐시·복호화 경로는 없다 — E2EE라 서버가 lock/unlock할 평문키 자체가 없음

---

## 안티패턴

- factory 함수 wrapper로 (인프라) 싱글톤 노출 → 직접 모듈 변수 (환경 분기/lazy 비용일 때만 예외)
- 모듈 수준 상수 블록 → `config.py` ABC + 환경별 서브클래스 + 팩토리
- 서버에서 시크릿/키 복호화 시도 → 서버는 ciphertext 그대로 저장만(E2EE), 도메인은 blob VO(`Ciphertext`)로 감싸기만
