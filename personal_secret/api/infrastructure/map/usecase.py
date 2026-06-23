from __future__ import annotations

import ast
import re
from pathlib import Path


# #
# usecase

# 흐름 추출은 본문 # label 단계 마커 순서를 따른다
_STEP = re.compile(r"^\s*#\s+([a-z][a-z_]*(?: [a-z_]+)*)\s*(?:$|[(—-])")
_REPOSITORY = re.compile(r"\b(\w+Repository)\b")


def build_usecases() -> list[dict]:
    directory = (
        Path(__file__)
        .resolve()
        .parent.parent.parent / "usecase"
    )
    usecases = [
        _read_usecase(path)
        for path in sorted(directory.glob("*.py"))
        if path.name != "__init__.py" and not path.name.startswith("_")
    ]
    return [
        usecase for usecase in usecases if usecase
    ]


def _read_usecase(path: Path) -> dict | None:
    source = path.read_text()
    tree = ast.parse(source)

    # action
    action = _action_def(tree)
    if action is None:
        return None

    name = path.stem
    lines = source.splitlines()
    body = lines[action.lineno - 1 : action.end_lineno]
    usecase = {
        "name": name,
        "aggregate": (
            name[: -len(action.name) - 1] if name.endswith(action.name) else name
        ),
        "action": action.name,
        "input": _input_fields(tree),
        "validations": _validations(action),
        "bindings": _bindings(action),
        "flow": _flow(action, lines, _bindings(action)),
        "output": _output(action),
        "repositories": _repositories(body),
    }
    return usecase


# 검증 = input 을 감싸는 도메인 VO 팩토리 (Email.from_str(input.email) → email 은 Email 로 검증)
def _validations(action) -> list[dict]:
    out, seen = [], set()
    for node in ast.walk(action):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and isinstance(node.func.value, ast.Name) and node.func.value.id[:1].isupper() \
                and node.func.attr.startswith("from_"):
            vo = node.func.value.id
            for inner in ast.walk(node):
                if isinstance(inner, ast.Attribute) and isinstance(inner.value, ast.Name) and inner.value.id == "input":
                    key = (inner.attr, vo)
                    if key not in seen:
                        seen.add(key)
                        out.append({"field": inner.attr, "vo": vo})
    return out


# 출력 = response dict (data·event…) + data 가 dict 면 한 단계 펼쳐 "무엇을 내보내나"
def _short_expr(node) -> str:
    txt = " ".join(ast.unparse(node).split())
    return txt[:54] + ("…" if len(txt) > 54 else "")


def _dict_entries(d) -> list[dict]:
    items = []
    for key, value in zip(d.keys, d.values):
        if key is None:
            items.append({"key": "…" + _short_expr(value), "expr": ""})
        elif isinstance(key, ast.Constant) and isinstance(key.value, str):
            items.append({"key": str(key.value), "expr": _short_expr(value)})
    return items


def _output(action) -> list[dict]:
    returns = [n for n in ast.walk(action) if isinstance(n, ast.Return) and isinstance(n.value, ast.Dict)]
    if not returns:
        return _output_call(action)
    keys_of = lambda d: [k.value for k in d.keys if isinstance(k, ast.Constant)]
    chosen = next((r for r in returns if "data" in keys_of(r.value)), returns[-1])
    out = []
    for key, value in zip(chosen.value.keys, chosen.value.values):
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            out.append({
                "key": str(key.value),
                "expr": _short_expr(value),
                "sub": _dict_entries(value) if isinstance(value, ast.Dict) else [],
            })
    return out


def _output_call(action) -> list[dict]:
    for node in ast.walk(action):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Call) \
                and isinstance(node.value.func, ast.Name) and node.value.func.id in ("Output", "Out"):
            return [
                {"key": kw.arg, "expr": _short_expr(kw.value), "sub": []}
                for kw in node.value.keywords if kw.arg
            ]
    return []


def _action_def(tree: ast.Module) -> ast.AsyncFunctionDef | ast.FunctionDef | None:
    for node in tree.body:
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) and not node.name.startswith("_"):
            return node
    return None


def _input_fields(tree: ast.Module) -> list[str]:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Input":
            return [
                statement.target.id
                for statement in node.body
                if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)
            ]
    return []


def _op_from_method(method: str) -> str | None:
    if method == "emit":
        return "event"
    if method.startswith("add"):
        return "create"
    if method.startswith(("update", "set")):
        return "update"
    if method.startswith(("remove", "delete")):
        return "delete"
    if method.startswith(("get", "find", "list", "exists", "filter")):
        return "read"
    return None


def _value_repo(node) -> str | None:
    for inner in ast.walk(node):
        if isinstance(inner, ast.Name) and inner.id.endswith("Repository"):
            return inner.id
    return None


def _target_names(target) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        return [el.id for el in target.elts if isinstance(el, ast.Name)]
    return []


# 변수 → repo 바인딩: entity = await XRepository.method(...) / (ev, entity) = Marker.kind(...Repo...)
# → entity 가 어느 도메인에서 왔는지 → 후속 필드(account.id 등)의 화살표 출발점

def _bindings(action) -> dict:
    out = {}
    for node in ast.walk(action):
        if not isinstance(node, ast.Assign):
            continue
        repo = _value_repo(node.value)
        if not repo:
            continue
        for target in node.targets:
            for nm in _target_names(target):
                if nm and nm != "_" and nm != "event" and not nm.endswith("_event"):
                    out[nm] = repo
    return out


# 필드 값 표현식의 직접 소스: input.x / 바인딩된 var.attr / 평범한 param
def _source(value, bindings: dict) -> dict | None:
    for inner in ast.walk(value):
        if isinstance(inner, ast.Attribute) and isinstance(inner.value, ast.Name) and inner.value.id == "input":
            return {"kind": "input", "name": inner.attr}
    for inner in ast.walk(value):
        if isinstance(inner, ast.Attribute) and isinstance(inner.value, ast.Name) and inner.value.id in bindings:
            return {"kind": "var", "var": inner.value.id, "attr": inner.attr}
    if isinstance(value, ast.Name):
        return {"kind": "param", "name": value.id}
    return None


def _kw_fields(call: ast.Call, bindings: dict) -> list[dict]:
    return [
        {"name": kw.arg, "src": _source(kw.value, bindings)}
        for kw in call.keywords if kw.arg and kw.arg != "session"
    ]


def _add_fields(step: dict, fields: list[dict]) -> None:
    have = {f["name"] for f in step["fields"]}
    for f in fields:
        if f["name"] not in have:
            step["fields"].append(f); have.add(f["name"])


# flow

# 각 AST 노드는 lineno 기준 직전 # label 에 귀속된다
def _flow(action, lines: list[str], bindings: dict) -> list[dict]:
    end = action.end_lineno or action.lineno
    labels = [
        (i, match.group(1))
        for i in range(action.lineno, end + 1)
        if (match := _STEP.match(lines[i - 1]))
    ]
    if not labels:
        return []

    steps = [
        {"label": label, "op": None, "repo": None, "method": None,
         "fields": [], "inputs": [], "repos": [], "event": None}
        for _, label in labels
    ]
    starts = [lineno for lineno, _ in labels]

    def bucket(lineno: int) -> dict:
        index = 0
        for i, start in enumerate(starts):
            if lineno >= start:
                index = i
        return steps[index]

    markers: list[str] = []
    for node in ast.walk(action):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "input":
            inputs = bucket(node.lineno)["inputs"]
            if node.attr not in inputs:
                inputs.append(node.attr)

        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        method = node.func.attr
        owner = node.func.value.id if isinstance(node.func.value, ast.Name) else None
        step = bucket(node.lineno)

        if owner and owner.endswith("Repository"):
            if owner not in step["repos"]:
                step["repos"].append(owner)
            step["repo"], step["method"] = owner, method
            op = _op_from_method(method)
            step["op"] = op or step["op"]
            if op in ("read", "delete"):
                _add_fields(step, _kw_fields(node, bindings))
            if method == "emit":
                # stamp
                step["event"] = {
                    "stamps": [kw.arg for kw in node.keywords if kw.arg and kw.arg not in ("session", "events")],
                    "records": [],
                }
        elif owner and owner[:1].isupper() and method == "new":
            # PascalCase.new(...) = 엔티티 생성 (allowlist 없이 구조로 판별)
            step["op"] = step["op"] or "create"
            _add_fields(step, _kw_fields(node, bindings))
        elif method.startswith("with_"):
            step["op"] = step["op"] or "update"
            arg = node.args[0] if node.args else (node.keywords[0].value if node.keywords else None)
            _add_fields(step, [{"name": method[len("with_"):], "src": _source(arg, bindings) if arg else None}])
        elif owner and owner.endswith("Event") and owner[:1].isupper() and method.islower() and not method.startswith("_"):
            # PascalCaseEvent.<kind>(...) = 도메인 이벤트 마커 (kind 고정 목록 없이 메서드명 그대로)
            markers.append(f"{owner[:-len('Event')].lower()}.{method}")

    emit_step = next((step for step in steps if step["event"]), None)
    if emit_step is not None:
        emit_step["event"]["records"] = markers
    return steps


def _repositories(body: list[str]) -> list[str]:
    seen = []
    for line in body:
        for name in _REPOSITORY.findall(line):
            if name not in seen:
                seen.append(name)
    return seen
