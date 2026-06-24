from __future__ import annotations

import ast
import re
from pathlib import Path

import personal_secret.api.infrastructure.map.client as client


API = Path(__file__).resolve().parent.parent.parent
MAP = client.map_client.build()


# #
# source ground truth

def _files(rel: str, pattern: str) -> list[Path]:
    return [p for p in sorted((API / rel).rglob(pattern)) if "__pycache__" not in str(p)]


def _domain_subclasses(base: str) -> list[str]:
    out = []
    for path in _files("domain", "*.py"):
        for node in ast.parse(path.read_text()).body:
            if isinstance(node, ast.ClassDef) and any(isinstance(b, ast.Name) and b.id == base for b in node.bases):
                out.append(node.name)
    return out


# #
# tables / rels

def test_tables_cover_every_model():
    declared = set()
    for path in _files("domain", "*.py"):
        declared.update(re.findall(r'__tablename__\s*=\s*"(\w+)"', path.read_text()))
    assert {t["name"] for t in MAP["tables"]} == declared


def test_sequence_column_unique():
    table = next(t for t in MAP["tables"] if t["name"] == "atomic_events")
    sequence = next(c for c in table["columns"] if c["name"] == "sequence")
    assert sequence["unique"] is True


def test_secrets_composite_unique():
    table = next(t for t in MAP["tables"] if t["name"] == "secrets")
    assert ["team_id", "domain", "service", "project", "field"] in table["composite_unique"]


def test_known_fk_rels_present():
    rels = {(r["from"], r["col"], r["to"]) for r in MAP["rels"]}
    assert ("account_tokens", "account_id", "accounts") in rels
    assert ("secrets", "team_id", "teams") in rels
    assert ("team_account", "account_id", "accounts") in rels


def test_no_spurious_actor_rel():
    edges = {(r["from"], r["col"]) for r in MAP["rels"]}
    assert ("atomic_events", "actor_id") not in edges
    assert ("atomic_events", "act_entity_id") not in edges


# #
# usecases / flow

def test_every_usecase_file_mapped():
    files = {p.stem for p in _files("usecase", "*.py") if p.name != "__init__.py" and not p.name.startswith("_")}
    assert {u["name"] for u in MAP["usecases"]} == files


def test_flow_step_and_op_schema():
    for usecase in MAP["usecases"]:
        for step in usecase["flow"]:
            assert set(step) == {"label", "ops", "inputs", "event"}
            for op in step["ops"]:
                assert set(op) == {"repo", "method", "op", "fields"}


def test_multi_repo_label_splits_into_ops():
    usecase = next(u for u in MAP["usecases"] if u["name"] == "team_invite")
    context = next(s for s in usecase["flow"] if s["label"] == "context")
    signature = {(op["repo"], op["method"], op["fields"][0]["src"]["name"]) for op in context["ops"]}
    assert ("AccountRepository", "get_by_id", "account_id") in signature
    assert ("TeamRepository", "get_by_id", "team_id") in signature


def test_usecase_context_params():
    reveal = next(u for u in MAP["usecases"] if u["name"] == "secret_reveal")
    assert reveal["context"] == ["event_group_id", "team_id", "account_id"]
    register = next(u for u in MAP["usecases"] if u["name"] == "auth_register")
    assert register["context"] == ["event_group_id"]
    notify = next(u for u in MAP["usecases"] if u["name"] == "notify_invited_member")
    assert notify["context"] == []


def test_search_and_verify_detected_as_read():
    ops = [op for u in MAP["usecases"] for s in u["flow"] for op in s["ops"]]
    assert any(op["method"] == "search" and op["op"] == "read" for op in ops)
    assert any(op["method"] == "verify_email" and op["op"] == "read" for op in ops)


# #
# endpoints

def test_endpoint_count_matches_routers():
    server = (API / "bin" / "server.py").read_text()
    assert len(MAP["endpoints"]) == len(re.findall(r"\bRouter\(", server))


def test_endpoint_usecases_resolve():
    names = {u["name"] for u in MAP["usecases"]}
    for endpoint in MAP["endpoints"]:
        if endpoint["usecase"] is not None:
            assert endpoint["usecase"] in names


# #
# repositories

def test_filter_by_event_id_is_a_read():
    row = next(
        (x for x in MAP["repositories"] if x["repo"] == "EventRepository" and x["method"] == "filter_by_event_id"),
        None,
    )
    assert row is not None
    assert row["where"] == ["event_id"]
    assert row["order_by"] == "sequence"
    assert row["card"] == "many"


def test_write_methods_excluded_from_reads():
    keys = {(x["repo"], x["method"]) for x in MAP["repositories"]}
    assert ("SecretRepository", "update") not in keys
    assert ("SecretRepository", "remove_by_id") not in keys
    assert ("EventRepository", "emit") not in keys


def test_repo_tables_cover_every_repository():
    repos = set()
    for path in _files("domain", "*_repository.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ClassDef) and node.name.endswith("Repository"):
                repos.add(node.name)
    assert set(MAP["repo_tables"]) == repos


# #
# domain

def test_value_objects_match_source():
    assert sorted(v["name"] for v in MAP["value_objects"]) == sorted(_domain_subclasses("ValueObject"))


def test_entities_match_source():
    assert sorted(e["name"] for e in MAP["entities"]) == sorted(_domain_subclasses("Entity"))


def test_events_match_source():
    assert sorted(e["name"] for e in MAP["events"]) == sorted(_domain_subclasses("Event"))


def test_value_scalar_types_rule_captured():
    value = next(v for v in MAP["value_objects"] if v["name"] == "Value")
    assert value["rules"]["scalar_types"] == ["str", "int", "float", "bool"]


# #
# exceptions

def _usecase_codes(name: str) -> set:
    return {(e["class"], e["origin"]) for e in MAP["exceptions"]["by_usecase"][name]}


def test_registry_covers_concrete_exceptions():
    registry = {e["class"]: e for e in MAP["exceptions"]["registry"]}
    assert registry["NotFoundError"]["code"] == 404
    assert registry["NotFoundError"]["category"] == "4xx"
    assert registry["DatabaseError"]["code"] == 500
    assert registry["DatabaseError"]["category"] == "5xx"


def test_input_validation_raises_traced():
    codes = _usecase_codes("auth_login")
    assert ("InvalidError", "input") in codes
    assert ("InvalidFormatError", "input") in codes


def test_domain_lookup_and_unique_raises_traced():
    assert ("NotFoundError", "domain") in _usecase_codes("secret_reveal")
    assert ("AlreadyExistsError", "domain") in _usecase_codes("secret_create")


def test_usecase_direct_raise_traced():
    assert ("InvalidCredentialError", "usecase") in _usecase_codes("auth_login")


def test_db_boundary_excludes_listen():
    db = {e["class"] for e in MAP["exceptions"]["adapter"]["db"]}
    assert "DatabaseError" in db
    assert "UniqueViolationError" in db
    assert "ListenError" not in db


def test_adapter_attached_by_called_method():
    login = {e["class"] for e in MAP["exceptions"]["by_usecase"]["auth_login"]}
    assert "VerifyError" in login          # argon2.verify
    assert "UnsupportedError" not in login  # sha256.verify 는 호출 안 함
    notify = {e["class"] for e in MAP["exceptions"]["by_usecase"]["notify_invited_member"]}
    assert "NotificationError" in notify


def test_unique_violation_only_on_write():
    reveal = {e["class"] for e in MAP["exceptions"]["by_usecase"]["secret_reveal"]}
    assert "UniqueViolationError" not in reveal
