# 싱글톤 + Config 패턴

외부 시스템 어댑터 인스턴스(`db_client`/`crypto`/`session_cache`)와 환경별 설정. `infrastructure/` + `config.py`에 산다.

루트: [api.md](../api.md) · repo: [repository.md](repository.md)

---

## 이 문서

| 섹션 | 핵심 규칙 |
|------|----------|
| **싱글톤** | 모듈 수준 직접 인스턴스화. factory wrapper 금지(환경분기·lazy만 예외) |
| **섹션 마커** | PascalCase 클래스명(`# Crypto`) — "이 블록은 default 인스턴스" |
| **Config** | `ABC` + 환경별 서브클래스 + `get_*_config()` 팩토리, `api/config.py`에 위치 |
| **crypto 은닉** | usecase는 `session_cache.encrypt/decrypt(bytes)`만, nonce/AEAD 포맷은 내부 |

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
crypto = Crypto(config=get_crypto_config())

# infrastructure/crypto/cache.py
# #
# SessionCache
session_cache = SessionCache(config=get_crypto_config())
```

```python
# 호출
from personal_secret.api.infrastructure.postgresql.client import db_client
db_client.method(...)
```

- **섹션 마커는 PascalCase 클래스명** — "이 블록은 해당 클래스의 default 인스턴스"(일반 lowercase 라벨의 예외). 여러 싱글톤은 각각 별도 섹션
- **factory 함수 wrapper 금지 — 예외**: ① 환경별 인스턴스 선택(Config) ② lazy 초기화 비용 큰 인스턴스

```python
# ❌ 불필요한 wrapper — 호출 시 () 빠뜨리면 AttributeError silent
_crypto = Crypto(...)
def crypto() -> Crypto:
    return _crypto
```

> **repository는 싱글톤이 아님** — classmethod 모음이라 인스턴스 없이 클래스 자체로 호출 (**[INV-6]**, [repository.md](repository.md)).

---

## Config 클래스

모듈 수준 상수 블록(`MAX_X = ...`) 대신 환경별 분기를 캡슐화.

- 위치: `personal_secret/api/config.py` — config는 `infrastructure/` 하위가 아니라 **api 루트**(여러 infra 어댑터가 공유)
- `ABC` + `@property @abstractmethod` 인터페이스 (`PostgresConfig(ABC)`)
- 프로퍼티명 = 환경변수 키와 동일한 UPPER_CASE
- 환경별 서브클래스 (`TestPostgresConfig`/`DevelopPostgresConfig`/`ProductionPostgresConfig`)
- 모듈 수준 팩토리 (`get_postgres_config()`) — Develop/Test/Production 분기라 factory 정당

---

## crypto 은닉

암호화 메커니즘은 infra 안에 숨긴다 — usecase는 `session_cache.encrypt(plaintext=...) -> bytes` / `decrypt(data=...) -> bytes`만 본다.

- DEK 조회·lock 확인(없으면 `LockedError`)은 `session_cache`, nonce 포맷·AEAD는 `crypto`가 소유
- 도메인은 결과 blob을 `Ciphertext.from_bytes(bytes=...)`로 감쌀 뿐 — 단일 blob VO(`to_bytes`/base64 `to_str`)라 crypto 내부 포맷을 모름

---

## 안티패턴

- ❌ factory 함수 wrapper로 (인프라) 싱글톤 노출 → 직접 모듈 변수 (환경 분기/lazy 비용일 때만 예외)
- ❌ 모듈 수준 상수 블록 → `config.py` ABC + 환경별 서브클래스 + 팩토리
- ❌ 암호화 내부 포맷(nonce/AEAD)을 usecase/도메인에 노출 → `session_cache`/`crypto`가 숨김, 도메인은 blob VO만
