from __future__ import annotations

import asyncio
import base64
import contextlib
import io
import os
import sys
import traceback
import uuid
from datetime import datetime, timedelta, timezone

# bootstrap path — personal_secret(루트) + factories(같은 폴더)
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)
sys.path.insert(0, _HERE)

from sqlalchemy import text

from personal_secret.api.infrastructure.database.postgresql.session import transactional_test_session_helper

from personal_secret.api.domain.common.exception import AlreadyExistsError

from personal_secret.api.domain.secret.secret_repository import SecretRepository
from personal_secret.api.domain.secret.secret_event import SecretEvent
from personal_secret.api.domain.account.account_event import AccountEvent
from personal_secret.api.domain.secret.domain import Domain
from personal_secret.api.domain.secret.service import Service
from personal_secret.api.domain.secret.project import Project
from personal_secret.api.domain.secret.field import Field
from personal_secret.api.domain.secret.ciphertext import Ciphertext

from personal_secret.api.domain.setting.setting_repository import SettingRepository
from personal_secret.api.domain.setting.key import Key
from personal_secret.api.domain.setting.value import Value
from personal_secret.api.domain.event.event.event_repository import EventRepository


from personal_secret.api.domain.account.account_repository import AccountRepository
from personal_secret.api.domain.team.team_repository import TeamRepository
from personal_secret.api.domain.team_access.team_access_repository import TeamAccessRepository
from personal_secret.api.domain.account_token.account_token_repository import AccountTokenRepository
from personal_secret.api.domain.account_token.fingerprint import Fingerprint
from personal_secret.api.domain.common.exception import InvalidCredentialError

from personal_secret.api.usecase import auth_register
from personal_secret.api.usecase import auth_login
from personal_secret.api.usecase import auth_get_only_salts
from personal_secret.api.usecase import team_create
from personal_secret.api.usecase import team_invite
from personal_secret.api.usecase import team_remove
from personal_secret.api.usecase import team_rotate
from personal_secret.api.usecase import account_get_only_public_key
from personal_secret.api.usecase import secret_reveal
from personal_secret.api.usecase import secret_search

from personal_secret.api.infrastructure.hash.sha256.client import sha256

from personal_secret.api.domain.common.exception import NotFoundError

from factories import make_secret, make_setting, make_account, make_token, make_team, make_account_team, DEFAULT_TEAM_ID


# #
# harness

async def expect_raises(exc_type, awaitable):
    try:
        await awaitable
    except exc_type:
        return
    except Exception as e:
        raise AssertionError(f"expected {exc_type.__name__}, got {type(e).__name__}: {e}")
    raise AssertionError(f"expected {exc_type.__name__}, nothing raised")


async def run_all(tests) -> int:
    passed, failed = 0, []
    for fn in tests:
        try:
            # 테스트마다 fresh schema + 격리 트랜잭션 (helper의 create/drop 로그는 억제)
            with contextlib.redirect_stdout(io.StringIO()):
                async with transactional_test_session_helper() as session:
                    await fn(session)
            print(f"  PASS  {fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {fn.__name__}  →  {type(e).__name__}: {e}")
            failed.append((fn.__name__, traceback.format_exc()))

    print(f"\n총 {passed + len(failed)}개 · 통과 {passed} · 실패 {len(failed)}")
    for name, tb in failed:
        print(f"\n--- {name} ---\n{tb}")
    return 1 if failed else 0


# #
# base CRUD (PostgresRepository — SecretRepository 통해 검증)

async def base_add_returns_persisted_with_timestamps(session):
    s = await SecretRepository.add(session=session, entity=make_secret(field="a"))
    assert s.field.to_str() == "a"
    assert s.created_at is not None and s.updated_at is not None  # server_default 채워짐
    assert s.deleted_at is None


async def base_find_by_id_found_and_missing(session):
    s = await SecretRepository.add(session=session, entity=make_secret(field="a"))
    found = await SecretRepository.find_by_id(session=session, id=s.id)
    assert found is not None and found.id == s.id
    assert await SecretRepository.find_by_id(session=session, id=uuid.uuid4()) is None


async def base_find_by_ids(session):
    a = await SecretRepository.add(session=session, entity=make_secret(field="a"))
    b = await SecretRepository.add(session=session, entity=make_secret(field="b"))
    got = await SecretRepository.find_by_ids(session=session, ids=[a.id, b.id])
    assert {x.id for x in got} == {a.id, b.id}
    assert await SecretRepository.find_by_ids(session=session, ids=[]) == []


async def base_exists_by_id(session):
    s = await SecretRepository.add(session=session, entity=make_secret(field="a"))
    assert await SecretRepository.exists_by_id(session=session, id=s.id) is True
    assert await SecretRepository.exists_by_id(session=session, id=uuid.uuid4()) is False


async def base_list_all_excludes_soft_deleted(session):
    await SecretRepository.add(session=session, entity=make_secret(field="a"))
    b = await SecretRepository.add(session=session, entity=make_secret(field="b"))
    await SecretRepository.remove_by_id(session=session, id=b.id)
    keys = {x.field.to_str() for x in await SecretRepository.list_all(session=session)}
    assert keys == {"a"}


async def base_update_persists_and_reloads(session):
    s = await SecretRepository.add(session=session, entity=make_secret(field="a", value=b"v1"))
    updated = await SecretRepository.update(session=session, entity=s.with_value(Ciphertext.from_bytes(b"v2")))
    assert updated.value.to_bytes() == b"v2"
    reloaded = await SecretRepository.find_by_id(session=session, id=s.id)
    assert reloaded.value.to_bytes() == b"v2"


async def base_update_many_returns_list(session):
    a = await SecretRepository.add(session=session, entity=make_secret(field="a"))
    b = await SecretRepository.add(session=session, entity=make_secret(field="b"))
    res = await SecretRepository.update_many(
        session=session,
        entities=[a.with_value(Ciphertext.from_bytes(b"1")), b.with_value(Ciphertext.from_bytes(b"2"))],
    )
    assert len(res) == 2 and all(r is not None for r in res)


# #
# SecretRepository (override + custom finder)

async def secret_update_missing_raises_notfound(session):
    # 추가 안 된 random id → base update None → override raise
    await expect_raises(NotFoundError, SecretRepository.update(session=session, entity=make_secret(field="ghost")))


async def secret_remove_by_id_soft_deletes(session):
    s = await SecretRepository.add(session=session, entity=make_secret(field="a"))
    removed = await SecretRepository.remove_by_id(session=session, id=s.id)
    assert removed.id == s.id
    assert await SecretRepository.find_by_id(session=session, id=s.id) is None


async def secret_remove_by_id_missing_raises_notfound(session):
    await expect_raises(NotFoundError, SecretRepository.remove_by_id(session=session, id=uuid.uuid4()))


async def secret_get_by_id_raises(session):
    await expect_raises(NotFoundError, SecretRepository.get_by_id(session=session, id=uuid.uuid4(), team_id=DEFAULT_TEAM_ID))


async def secret_get_by_id_other_team_not_found(session):
    s = await SecretRepository.add(session=session, entity=make_secret(team_id=DEFAULT_TEAM_ID, field="a"))
    # 다른 팀에서 같은 id 조회 → 존재해도 NotFound
    await expect_raises(NotFoundError, SecretRepository.get_by_id(session=session, id=s.id, team_id=uuid.uuid4()))


async def secret_find_by_path(session):
    s = await SecretRepository.add(
        session=session,
        entity=make_secret(domain="ssh", service="github", project="prod", field="password"),
    )
    got = await SecretRepository.find_by_path(
        session=session,
        team_id=DEFAULT_TEAM_ID,
        domain=Domain.from_str("ssh"),
        service=Service.from_str("github"),
        project=Project.from_str("prod"),
        field=Field.from_str("password"),
    )
    assert got is not None and got.id == s.id
    # 한 조각만 달라도 미스
    assert await SecretRepository.find_by_path(
        session=session,
        team_id=DEFAULT_TEAM_ID,
        domain=Domain.from_str("ssh"),
        service=Service.from_str("github"),
        project=Project.from_str("test"),
        field=Field.from_str("password"),
    ) is None


async def secret_search_by_scope(session):
    await SecretRepository.add(session=session, entity=make_secret(domain="ssh", service="github", project="prod", field="a"))
    await SecretRepository.add(session=session, entity=make_secret(domain="ssh", service="github", project="test", field="b"))
    await SecretRepository.add(session=session, entity=make_secret(domain="web", service="site", project="prod", field="c"))

    t = DEFAULT_TEAM_ID
    # domain 필터
    assert {x.field.to_str() for x in await SecretRepository.search(session=session, team_id=t, domain=Domain.from_str("ssh"))} == {"a", "b"}
    # service 필터
    assert {x.field.to_str() for x in await SecretRepository.search(session=session, team_id=t, service=Service.from_str("github"))} == {"a", "b"}
    # project 필터
    assert {x.field.to_str() for x in await SecretRepository.search(session=session, team_id=t, project=Project.from_str("prod"))} == {"a", "c"}
    # combo
    res = await SecretRepository.search(session=session, team_id=t, domain=Domain.from_str("ssh"), project=Project.from_str("test"))
    assert [x.field.to_str() for x in res] == ["b"]
    # 조건 없음 → 그 팀 전체(key 정렬)
    assert [x.field.to_str() for x in await SecretRepository.search(session=session, team_id=t)] == ["a", "b", "c"]


async def secret_search_scoped_to_team(session):
    other = uuid.uuid4()
    await SecretRepository.add(session=session, entity=make_secret(team_id=DEFAULT_TEAM_ID, field="mine"))
    await SecretRepository.add(session=session, entity=make_secret(team_id=other, field="theirs"))
    mine = await SecretRepository.search(session=session, team_id=DEFAULT_TEAM_ID)
    assert {x.field.to_str() for x in mine} == {"mine"}    # 다른 팀 것 안 보임


async def secret_search_pagination(session):
    for k in ["a", "b", "c", "d"]:
        await SecretRepository.add(session=session, entity=make_secret(field=k))
    page1 = await SecretRepository.search(session=session, team_id=DEFAULT_TEAM_ID, limit=2)
    page2 = await SecretRepository.search(session=session, team_id=DEFAULT_TEAM_ID, limit=2, offset=2)
    assert [x.field.to_str() for x in page1] == ["a", "b"]
    assert [x.field.to_str() for x in page2] == ["c", "d"]


async def secret_add_unique_by_path_duplicate_raises_already_exists(session):
    # 사전검사: 같은 (team,domain,service,project,key) → AlreadyExistsError(409)
    await SecretRepository.add_unique_by_path(session=session, entity=make_secret(field="dup"))
    try:
        await SecretRepository.add_unique_by_path(session=session, entity=make_secret(field="dup"))
        assert False, "expected AlreadyExistsError"
    except AlreadyExistsError as exc:
        assert exc.code == 409 and "dup" in exc.msg


async def secret_add_unique_by_path_same_path_different_team_ok(session):
    # 같은 경로라도 팀이 다르면 충돌 없음 (team_id 가 unique 에 포함)
    await SecretRepository.add_unique_by_path(session=session, entity=make_secret(team_id=DEFAULT_TEAM_ID, field="dup"))
    b = await SecretRepository.add_unique_by_path(session=session, entity=make_secret(team_id=uuid.uuid4(), field="dup"))
    assert b.id is not None


async def secret_soft_deleted_path_reusable(session):
    a = await SecretRepository.add_unique_by_path(session=session, entity=make_secret(field="dup"))
    await SecretRepository.remove_by_id(session=session, id=a.id)
    # partial unique index(WHERE deleted_at IS NULL) → 재사용 허용
    b = await SecretRepository.add_unique_by_path(session=session, entity=make_secret(field="dup"))
    assert b.id != a.id
    got = await SecretRepository.find_by_path(
        session=session,
        team_id=DEFAULT_TEAM_ID,
        domain=Domain.from_str("ssh"),
        service=Service.from_str("github"),
        project=Project.from_str("prod"),
        field=Field.from_str("dup"),
    )
    assert got.id == b.id


async def secret_rls_db_level_isolation(session):
    # superuser 는 RLS 우회 → savepoint 안에서 임시 비superuser role 로 실제 차단 검증
    a, b = DEFAULT_TEAM_ID, uuid.uuid4()
    await SecretRepository.add(session=session, entity=make_secret(team_id=a, field="mine"))
    await SecretRepository.add(session=session, entity=make_secret(team_id=b, field="theirs"))
    nested = await session.begin_nested()
    try:
        await session.execute(text("CREATE ROLE rls_probe NOSUPERUSER"))
        await session.execute(text("GRANT SELECT ON secrets TO rls_probe"))
        await session.execute(text("SET ROLE rls_probe"))
        await session.execute(text("SELECT set_config('app.current_team', :t, true)"), {"t": str(a)})
        # list_all 은 team_id WHERE 가 없는 base 메서드 — 그래도 RLS 가 A 만 통과시킴
        rows = await SecretRepository.list_all(session=session)
        await session.execute(text("RESET ROLE"))
    finally:
        await nested.rollback()
    assert {x.field.to_str() for x in rows} == {"mine"}


# #
# SettingRepository (KV)

async def setting_find_by_key(session):
    await SettingRepository.add(session=session, entity=make_setting(key="app.theme", value="dark"))
    got = await SettingRepository.find_by_key(session=session, key=Key.from_str("app.theme"))
    assert got.value.to_json() == "dark"
    assert await SettingRepository.find_by_key(session=session, key=Key.from_str("missing")) is None


async def setting_get_by_key_raises(session):
    await expect_raises(NotFoundError, SettingRepository.get_by_key(session=session, key=Key.from_str("missing")))


async def setting_set_by_key_insert_then_update(session):
    a = await SettingRepository.set_by_key(session=session, key=Key.from_str("k"), value=Value.from_json("v1"))
    assert a.value.to_json() == "v1"
    b = await SettingRepository.set_by_key(session=session, key=Key.from_str("k"), value=Value.from_json("v2"))
    assert b.id == a.id and b.value.to_json() == "v2"  # 같은 행 갱신
    assert len(await SettingRepository.list_all(session=session)) == 1  # 행 1개


async def setting_list_pagination(session):
    for k in ["a.x", "b.y", "c.z"]:
        await SettingRepository.set_by_key(session=session, key=Key.from_str(k), value=Value.from_json("v"))
    page1 = await SettingRepository.list_all(session=session, limit=2)
    page2 = await SettingRepository.list_all(session=session, limit=2, offset=2)
    assert [s.key.to_str() for s in page1] == ["a.x", "b.y"]   # key 정렬
    assert [s.key.to_str() for s in page2] == ["c.z"]


async def setting_set_by_key_value_types(session):
    await SettingRepository.set_by_key(session=session, key=Key.from_str("num"), value=Value.from_json(42))
    await SettingRepository.set_by_key(session=session, key=Key.from_str("list"), value=Value.from_json(["a", "b"]))
    assert (await SettingRepository.get_by_key(session=session, key=Key.from_str("num"))).value.to_json() == 42
    assert (await SettingRepository.get_by_key(session=session, key=Key.from_str("list"))).value.to_json() == ["a", "b"]


# #
# EventRepository (emit)

async def event_emit_stores_with_marker_id(session):
    secret = await SecretRepository.add(session=session, entity=make_secret(field="a"))
    event, _ = SecretEvent.created(secret=secret)
    group = uuid.uuid4()
    stored = await EventRepository.emit(session=session, id=group, name="test", atomics=[event])
    assert len(stored) == 1
    e = stored[0]
    assert e.id == event.id()                      # identity는 마커가 확정
    assert e.act_entity_name.to_str() == "secret"
    assert e.act.to_str() == "created"
    assert e.act_entity_id == secret.id
    assert e.event_id == group                      # emit이 호출자 묶음(Event) id 스탬프
    found = await EventRepository.find_by_id(session=session, id=group)
    assert found.name.to_str() == "test"


async def event_emit_multiple_shares_act_group(session):
    secret = await SecretRepository.add(session=session, entity=make_secret(field="a"))
    group = uuid.uuid4()
    stored = await EventRepository.emit(
        session=session,
        id=group,
        name="test",
        atomics=[SecretEvent.updated(secret=secret)[0], SecretEvent.deleted(secret=secret)[0]],
    )
    assert len(stored) == 2
    assert {s.act.to_str() for s in stored} == {"updated", "deleted"}
    assert {s.act_entity_name.to_str() for s in stored} == {"secret"}
    assert stored[0].event_id == stored[1].event_id == group   # 같은 emit = 같은 Event


# #
# EventRepository (actor · payload · sequence)

async def event_emit_stamps_actor_and_team(session):
    secret = await SecretRepository.add(
        session=session,
        entity=make_secret(domain="ssh", service="github", project="prod", field="password"),
    )
    actor = uuid.uuid4()
    [event] = await EventRepository.emit(
        session=session,
        id=uuid.uuid4(),
        name="test",
        atomics=[SecretEvent.created(secret=secret)[0]],
        actor_id=actor,
        actor_team_id=secret.team_id,
    )
    assert event.payload.to_dict() == {"domain": "ssh", "service": "github", "project": "prod", "field": "password"}
    assert event.sequence is not None                # DB Identity 발급
    assert event.actor_id == actor                   # emit이 행위자 스탬프
    assert event.actor_team_id == secret.team_id     # RLS 테넌트


async def event_emit_global_has_no_actor_team(session):
    account = await AccountRepository.add_unique_by_email(session=session, entity=make_account())
    [event] = await EventRepository.emit(
        session=session,
        id=uuid.uuid4(),
        name="test",
        atomics=[AccountEvent.created(account=account)[0]],
    )
    assert event.act_entity_name.to_str() == "account"
    assert event.actor_team_id is None               # global(RLS 밖) → None
    assert event.actor_id is None                    # 미전달 → None


async def secret_reveal_emits_read_event(session):
    secret = await SecretRepository.add(session=session, entity=make_secret(field="a"))
    actor = uuid.uuid4()
    event_group_id = uuid.uuid4()
    await secret_reveal.reveal(
        session=session,
        event_group_id=event_group_id,
        input=secret_reveal.Input(id=str(secret.id)),
        team_id=secret.team_id,
        account_id=actor,
    )
    atomics = await EventRepository.filter_by_event_id(session=session, event_id=event_group_id)
    reads = [e for e in atomics if e.act.to_str() == "read"]
    assert len(reads) == 1
    assert reads[0].act_entity_id == secret.id       # 어떤 시크릿을
    assert reads[0].actor_id == actor                # 누가 읽었나
    assert reads[0].actor_team_id == secret.team_id


async def secret_list_emits_read_per_result_sharing_act_group(session):
    team = uuid.uuid4()
    actor = uuid.uuid4()
    for field in ["a", "b", "c"]:
        await SecretRepository.add(session=session, entity=make_secret(team_id=team, field=field))
    event_group_id = uuid.uuid4()
    listed = await secret_search.search(
        session=session,
        event_group_id=event_group_id,
        input=secret_search.Input(),
        team_id=team,
        account_id=actor,
    )
    assert len(listed.data) == 3
    atomics = await EventRepository.filter_by_event_id(session=session, event_id=event_group_id)
    reads = [e for e in atomics if e.act.to_str() == "read"]
    assert len(reads) == 3                              # 결과당 1건
    assert len({e.event_id for e in reads}) == 1       # 같은 Event 로 묶임
    assert {e.actor_id for e in reads} == {actor}
    assert {e.actor_team_id for e in reads} == {team}


# #
# auth (account + token)

def _register_input(*, email="me@example.com", login_proof="proof-xyz"):
    b64 = lambda raw: base64.b64encode(raw).decode("ascii")
    return auth_register.Input(
        email=email,
        personal_lock=b64(b"public-key"),
        personal_locked_key=b64(b"locked-private-key"),
        personal_unlock_salt=b64(b"unlock-salt"),
        login_salt=b64(b"login-salt"),
        login_proof=login_proof,
        team_locked_key=b64(b"personal-team-locked-key"),
    )


async def account_find_by_email(session):
    a = await AccountRepository.add(session=session, entity=make_account(email="me@example.com"))
    got = await AccountRepository.find_by_email(session=session, email=a.email)
    assert got is not None and got.id == a.id


async def auth_register_creates_account(session):
    result = await auth_register.register(session=session, event_group_id=uuid.uuid4(), input=_register_input())
    assert result.data["email"] == "me@example.com"
    # 검증값·키 평문은 응답에 없음
    assert "login_verifier" not in result.data and "login_proof" not in result.data


async def auth_register_creates_personal_team(session):
    result = await auth_register.register(session=session, event_group_id=uuid.uuid4(), input=_register_input())
    team_id = uuid.UUID(result.data["personal_team_id"])
    account = await AccountRepository.find_by_email(session=session, email=make_account().email)
    membership = await TeamAccessRepository.find_by_account_and_team(
        session=session, account_id=account.id, team_id=team_id,
    )
    assert membership is not None and membership.role.to_str() == "owner"


async def auth_register_duplicate_email_raises(session):
    await auth_register.register(session=session, event_group_id=uuid.uuid4(), input=_register_input(email="me@example.com"))
    await expect_raises(
        AlreadyExistsError,
        auth_register.register(session=session, event_group_id=uuid.uuid4(), input=_register_input(email="me@example.com")),
    )


async def auth_login_issues_token_bound_to_account(session):
    await auth_register.register(session=session, event_group_id=uuid.uuid4(), input=_register_input(login_proof="proof-xyz"))
    account = await AccountRepository.find_by_email(session=session, email=make_account().email)
    result = await auth_login.login(
        session=session,
        event_group_id=uuid.uuid4(),
        input=auth_login.Input(email="me@example.com", login_proof="proof-xyz"),
    )
    raw = result.data["token"]
    assert raw and result.data["expires_at"]
    # 키 자료 동봉 (클라가 personal_key 복원용)
    assert result.data["personal_locked_key"] and result.data["personal_unlock_salt"]
    # 저장은 fingerprint, 토큰은 account 에 묶임
    stored = await AccountTokenRepository.find_by_fingerprint(session=session, fingerprint=Fingerprint.from_str(sha256.hash(value=raw)))
    assert stored is not None and stored.account_id == account.id


async def auth_login_wrong_proof_raises(session):
    await auth_register.register(session=session, event_group_id=uuid.uuid4(), input=_register_input(login_proof="proof-xyz"))
    await expect_raises(
        InvalidCredentialError,
        auth_login.login(
            session=session,
            event_group_id=uuid.uuid4(),
            input=auth_login.Input(email="me@example.com", login_proof="wrong"),
        ),
    )


async def auth_salts_returns_login_and_unlock_salt(session):
    await auth_register.register(session=session, event_group_id=uuid.uuid4(), input=_register_input())
    result = await auth_get_only_salts.get_only_salts(
        session=session,
        event_group_id=uuid.uuid4(),
        input=auth_get_only_salts.Input(email="me@example.com"),
    )
    assert result.data["personal_unlock_salt"] and result.data["login_salt"]


async def token_find_by_fingerprint_and_expiry(session):
    now = datetime.now(timezone.utc)
    account = await AccountRepository.add(session=session, entity=make_account())
    live = await AccountTokenRepository.add(session=session, entity=make_token(account_id=account.id, raw="abc"))
    got = await AccountTokenRepository.find_by_fingerprint(session=session, fingerprint=Fingerprint.from_str(sha256.hash(value="abc")))
    assert got.id == live.id and got.is_expired(now=now) is False
    expired = await AccountTokenRepository.add(
        session=session,
        entity=make_token(account_id=account.id, raw="old", expires_at=now - timedelta(hours=1)),
    )
    assert expired.is_expired(now=now) is True


# #
# tenancy (team + account_team)

async def team_create_makes_team_and_owner_membership(session):
    account = await AccountRepository.add(session=session, entity=make_account())
    b64 = base64.b64encode(b"team-locked-key").decode("ascii")
    result = await team_create.create(
        session=session,
        event_group_id=uuid.uuid4(),
        input=team_create.Input(name="acme", team_locked_key=b64),
        account_id=account.id,
    )
    team_id = uuid.UUID(result.data["id"])
    membership = await TeamAccessRepository.find_by_account_and_team(
        session=session, account_id=account.id, team_id=team_id,
    )
    assert membership is not None and membership.role.to_str() == "owner"


async def account_team_unique_per_account_and_team(session):
    account = await AccountRepository.add(session=session, entity=make_account())
    team = await TeamRepository.add(session=session, entity=make_team())
    await TeamAccessRepository.add_unique_by_account_and_team(
        session=session, entity=make_account_team(account_id=account.id, team_id=team.id),
    )
    await expect_raises(
        AlreadyExistsError,
        TeamAccessRepository.add_unique_by_account_and_team(
            session=session, entity=make_account_team(account_id=account.id, team_id=team.id),
        ),
    )


async def account_team_filter_by_team(session):
    team = await TeamRepository.add(session=session, entity=make_team())
    a1 = await AccountRepository.add(session=session, entity=make_account(email="a@example.com"))
    a2 = await AccountRepository.add(session=session, entity=make_account(email="b@example.com"))
    await TeamAccessRepository.add(session=session, entity=make_account_team(account_id=a1.id, team_id=team.id))
    await TeamAccessRepository.add(session=session, entity=make_account_team(account_id=a2.id, team_id=team.id, role="member"))
    members = await TeamAccessRepository.filter_by_team(session=session, team_id=team.id)
    assert {m.account_id for m in members} == {a1.id, a2.id}


# #
# member management (invite · remove · rotate)

async def account_public_key_lookup(session):
    a = await AccountRepository.add(session=session, entity=make_account(email="me@example.com"))
    result = await account_get_only_public_key.get_only_public_key(
        session=session,
        event_group_id=uuid.uuid4(),
        input=account_get_only_public_key.Input(email="me@example.com"),
    )
    assert result.data["account_id"] == str(a.id) and result.data["personal_lock"]


async def team_invite_adds_membership(session):
    invitee = await AccountRepository.add(session=session, entity=make_account(email="bob@example.com"))
    team = await TeamRepository.add(session=session, entity=make_team())
    sealed = base64.b64encode(b"team-key-sealed-for-bob").decode("ascii")
    await team_invite.invite(
        session=session,
        event_group_id=uuid.uuid4(),
        input=team_invite.Input(account_id=str(invitee.id), role="member", team_locked_key=sealed),
        team_id=team.id,
    )
    m = await TeamAccessRepository.find_by_account_and_team(session=session, account_id=invitee.id, team_id=team.id)
    assert m is not None and m.role.to_str() == "member"


async def team_remove_deletes_membership(session):
    account = await AccountRepository.add(session=session, entity=make_account())
    team = await TeamRepository.add(session=session, entity=make_team())
    await TeamAccessRepository.add(session=session, entity=make_account_team(account_id=account.id, team_id=team.id))
    await team_remove.remove(
        session=session,
        event_group_id=uuid.uuid4(),
        input=team_remove.Input(account_id=str(account.id)),
        team_id=team.id,
    )
    assert await TeamAccessRepository.find_by_account_and_team(session=session, account_id=account.id, team_id=team.id) is None


async def team_remove_missing_raises(session):
    team = await TeamRepository.add(session=session, entity=make_team())
    await expect_raises(
        NotFoundError,
        team_remove.remove(
            session=session,
            event_group_id=uuid.uuid4(),
            input=team_remove.Input(account_id=str(uuid.uuid4())),
            team_id=team.id,
        ),
    )


async def team_rotate_reencrypts_and_rekeys(session):
    account = await AccountRepository.add(session=session, entity=make_account())
    team = await TeamRepository.add(session=session, entity=make_team())
    await TeamAccessRepository.add(session=session, entity=make_account_team(account_id=account.id, team_id=team.id))
    secret = await SecretRepository.add(session=session, entity=make_secret(team_id=team.id, field="db", value=b"old"))

    new_value = base64.b64encode(b"new-ciphertext").decode("ascii")
    new_key = base64.b64encode(b"new-sealed-team-key").decode("ascii")
    result = await team_rotate.rotate(
        session=session,
        event_group_id=uuid.uuid4(),
        input=team_rotate.Input(
            secrets={str(secret.id): new_value},
            members={str(account.id): new_key},
        ),
        team_id=team.id,
    )
    assert result.data["secrets_reencrypted"] == 1 and result.data["members_rekeyed"] == 1
    # 시크릿 value 와 멤버 team_locked_key 가 새 값으로 교체됨
    reloaded = await SecretRepository.get_by_id(session=session, id=secret.id, team_id=team.id)
    assert reloaded.value.to_str() == new_value
    m = await TeamAccessRepository.find_by_account_and_team(session=session, account_id=account.id, team_id=team.id)
    assert m.team_locked_key.to_str() == new_key


TESTS = [
    base_add_returns_persisted_with_timestamps,
    base_find_by_id_found_and_missing,
    base_find_by_ids,
    base_exists_by_id,
    base_list_all_excludes_soft_deleted,
    base_update_persists_and_reloads,
    base_update_many_returns_list,
    secret_update_missing_raises_notfound,
    secret_remove_by_id_soft_deletes,
    secret_remove_by_id_missing_raises_notfound,
    secret_get_by_id_raises,
    secret_get_by_id_other_team_not_found,
    secret_find_by_path,
    secret_search_by_scope,
    secret_search_scoped_to_team,
    secret_search_pagination,
    secret_add_unique_by_path_duplicate_raises_already_exists,
    secret_add_unique_by_path_same_path_different_team_ok,
    secret_soft_deleted_path_reusable,
    secret_rls_db_level_isolation,
    setting_find_by_key,
    setting_get_by_key_raises,
    setting_set_by_key_insert_then_update,
    setting_set_by_key_value_types,
    setting_list_pagination,
    event_emit_stores_with_marker_id,
    event_emit_multiple_shares_act_group,
    event_emit_stamps_actor_and_team,
    event_emit_global_has_no_actor_team,
    secret_reveal_emits_read_event,
    secret_list_emits_read_per_result_sharing_act_group,
    account_find_by_email,
    auth_register_creates_account,
    auth_register_creates_personal_team,
    auth_register_duplicate_email_raises,
    auth_login_issues_token_bound_to_account,
    auth_login_wrong_proof_raises,
    auth_salts_returns_login_and_unlock_salt,
    token_find_by_fingerprint_and_expiry,
    team_create_makes_team_and_owner_membership,
    account_team_unique_per_account_and_team,
    account_team_filter_by_team,
    account_public_key_lookup,
    team_invite_adds_membership,
    team_remove_deletes_membership,
    team_remove_missing_raises,
    team_rotate_reencrypts_and_rekeys,
]


if __name__ == "__main__":
    sys.exit(asyncio.run(run_all(TESTS)))
