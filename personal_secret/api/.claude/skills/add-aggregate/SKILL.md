---
description: 새 aggregate를 도메인(VO·Entity·Repository·Event)부터 usecase·endpoint·bin/server 등록까지 전 수직 슬라이스로 추가할 때. DDD aggregate 신규 생성 절차.
---

# Recipe: Aggregate 추가 (전 수직 슬라이스)

새 aggregate(`secret` 같은) 전체를 도메인→API까지. 가장 큰 수직 작업 — 아래 reference를 이 순서로 읽으며 진행한다.

선행: [conventions.md](../../../../../.claude/rules/shared/conventions.md) 1회. 배치 판단은 아래 절차 순서가 곧 권위다.

## 절차

1. ValueObject들 — `domain/{agg}/{value}.py` 각각. → [recipe/add-value-object](../add-value-object/SKILL.md), 규칙 [reference/value-object.md](../../../../../.claude/rules/api/value-object.md)
2. Entity — `domain/{agg}/{agg}.py`. `new` 팩토리 + `to_dict`/`to_model` + `with_X`. → [reference/entity.md](../../../../../.claude/rules/api/entity.md)
3. Repository + Model — `domain/{agg}/{agg}_repository.py` 한 파일에 `{Agg}Model`(SQLAlchemy) + `_to_{agg}` mapper + `{Agg}Repository(PostgresRepository[..])`. class vars `model`/`mapper`만으로 CRUD 동작, 커스텀 finder는 `@classmethod` delegation. unique 필요하면 `{action}_unique_by_{col}`. → [reference/repository.md](../../../../../.claude/rules/api/repository.md)
   - 2개 이상 aggregate에 같은 패턴 반복이면 `PostgresRepository`(infra)로 끌어올림 ([reference/repository.md](../../../../../.claude/rules/api/repository.md) "일반화 부모")
4. Event 마커(필요시) — `domain/{agg}/{agg}_event.py` 순수 마커(`act`/`act_entity_name`/`act_entity_id`/`payload` 접근자) + `domain/event/act.py` `Act._allowed_list`·`entity_name.py` `EntityName._allowed_list`에 새 act·name 미러링. → [reference/domain-event.md](../../../../../.claude/rules/api/domain-event.md)
5. UseCase들 — `usecase/{agg}_{action}.py` 동작마다(폴더 없이 평탄). → [recipe/add-usecase](../add-usecase/SKILL.md)
6. Endpoint 핸들러 — `endpoint/{agg}.py`에 `post_create` 등(HTTP 메서드 접두). → [reference/endpoint.md](../../../../../.claude/rules/api/endpoint.md)
7. 등록 — `bin/server.py`에서 `from ...endpoint import {agg}` + `server.router(Router(path=..., methods=..., endpoint={agg}.post_create))`. → [reference/server.md](../../../../../.claude/rules/api/server.md)
8. 예외(새 카테고리 필요시) — [recipe/add-exception](../add-exception/SKILL.md)

## 체크

- [ ] import 방향 위→아래만 (**[INV-1]**) — domain repo가 `PostgresRepository` 상속하는 완화는 OK
- [ ] 중간 파일(`infrastructure/postgresql/{agg}_repository.py`) 안 만들었나 → domain repo 직접 상속
- [ ] 등록을 endpoint 아닌 `bin/server.py`에 했나
- [ ] Event act/name을 마커 enum + `Act._allowed_list`·`EntityName._allowed_list` 갱신했나
