# Recipe: ValueObject 추가

도메인 값 하나를 VO로 추가. 규칙 본문은 [reference/value-object.md](../reference/value-object.md), 여기선 순서만.

선행: [conventions.md](../conventions.md) 1회.

## 절차

1. **파일** — `domain/{aggregate}/{value}.py` (파일명 = snake_case value명, 폴더 컨텍스트 중복 금지)
2. **팩토리 종류 선택** — 단순 `from_str` / 복합 `from_dict` / 시간 `from_datetime` / 플래그 `from_bool` / 수량 `from_int` / blob `from_bytes`
3. **dataclass 작성** — `@dataclass(frozen=True, kw_only=True)`, 필드 `_` 접두, `ValueObject` 상속
4. **팩토리 메서드** — `@classmethod`, 단일 `value` positional, **검증 순서 type→format→range**(예외는 [reference/exception.md](../reference/exception.md): 타입 `InvalidError`, 형식 `InvalidFormatError`), 끝에 `by_factory=True`
5. **변환 메서드** — `to_str`/`to_dict`/... (시간 VO는 `+ to_datetime`, blob VO는 `+ to_bytes`)
6. **enum 성격이면** — `_allowed_list: tuple[str, ...]` hint 추가
7. **사용처 연결** — Entity 필드 타입 교체([reference/entity.md](../reference/entity.md)), `to_dict`/`to_model`에서 `value.to_*()` 호출

## 체크

- [ ] `by_factory=True` 빠짐 없나 (**[INV-2]**)
- [ ] raw primitive를 안 남겼나 — UUID/audit 외 전부 VO (**[INV-10]**)
- [ ] 직접 생성(`Name(_value=...)`) 호출처 없나 → 팩토리만
