from __future__ import annotations

import ast
from pathlib import Path

from personal_secret.api.infrastructure.map.source import parse_source


# #
# exception

def build_exceptions(usecases: list[dict]) -> dict:
    registry = _registry()
    catalog = _catalog()
    vo = _vo_raises(registry)
    method = _method_raises(registry)
    direct = _usecase_raises(registry)
    adapter = _adapter_catalog(registry)
    adapter_methods = _adapter_methods(registry)
    behavior = _scope_raises(_behavior_files(), registry)
    return {
        "registry": [
            _entry(name, registry, catalog)
            for name in sorted(registry)
            if registry[name]["code"]
        ],
        "by_usecase": {
            uc["name"]: _compose(uc, registry, catalog, vo, method, direct, adapter, adapter_methods)
            for uc in usecases
        },
        "behavior": [_entry(name, registry, catalog) for name in behavior],
        "adapter": {
            key: [_entry(name, registry, catalog) for name in names]
            for key, names in adapter.items()
        },
    }


def _entry(name: str, registry: dict, catalog: dict) -> dict:
    meta = registry[name]
    return {
        "class": name,
        "code": meta["code"],
        "category": meta["category"],
        "key": meta["key"],
        "layer": meta["layer"],
        "message": catalog.get(meta["key"], ""),
    }


def _compose(uc, registry, catalog, vo, method, direct, adapter, adapter_methods) -> list[dict]:
    out, seen = [], set()

    def add(name: str, origin: str, via: str) -> None:
        if name not in registry or not registry[name]["code"]:
            return
        if (name, origin, via) in seen:
            return
        seen.add((name, origin, via))
        out.append({**_entry(name, registry, catalog), "origin": origin, "via": via})

    # input
    for validation in uc.get("validations", []):
        for name in vo.get(validation["vo"], []):
            add(name, "input", validation["field"])

    # domain
    has_op = has_write = False
    for step in uc.get("flow", []):
        for op in step.get("ops", []):
            if not op.get("repo") or not op.get("method"):
                continue
            has_op = True
            if op.get("op") in ("create", "update", "delete"):
                has_write = True
            for name in method.get((op["repo"], op["method"]), []):
                add(name, "domain", f'{op["repo"]}.{op["method"]}')

    # usecase
    for name in direct.get(uc["name"], []):
        add(name, "usecase", uc["name"])

    # db
    if has_op:
        for name in adapter.get("db", []):
            if registry[name]["code"] == 409 and not has_write:
                continue
            add(name, "db", "transactional_session")

    # infra
    for instance, method_name in _usecase_adapter_calls(uc["name"], adapter_methods):
        for name in adapter_methods[instance].get(method_name, []):
            add(name, "infra", f"{instance}.{method_name}")

    return out


# #
# registry

def _registry() -> dict:
    bases, meta = {}, {}
    for path in _exception_files():
        layer = _layer(path)
        for node in ast.walk(parse_source(path)):
            if not isinstance(node, ast.ClassDef):
                continue
            bases[node.name] = [b.id for b in node.bases if isinstance(b, ast.Name)]
            code, key = _init_facts(node)
            meta[node.name] = {"code": code, "key": key, "layer": layer}
    return {
        name: {**meta[name], "category": _category(name, bases)}
        for name in meta
        if _category(name, bases)
    }


def _exception_files() -> list[Path]:
    root = _api_root()
    return [
        path
        for path in sorted(root.rglob("exception.py"))
        if "__pycache__" not in str(path) and path.parent.name != "server"
    ]


def _init_facts(node: ast.ClassDef) -> tuple:
    for member in node.body:
        if not (isinstance(member, ast.FunctionDef) and member.name == "__init__"):
            continue
        for inner in ast.walk(member):
            if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute) \
                    and inner.func.attr == "__init__" and _is_super(inner.func.value):
                kw = {k.arg: k.value for k in inner.keywords if k.arg}
                code_node, key_node = kw.get("code"), kw.get("key")
                code = code_node.value if isinstance(code_node, ast.Constant) else None
                key = key_node.value if isinstance(key_node, ast.Constant) else None
                return code, key
    return None, None


def _is_super(node) -> bool:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "super"


def _category(name: str, bases: dict) -> str | None:
    stack, seen = [name], set()
    while stack:
        current = stack.pop()
        if current == "ClientError":
            return "4xx"
        if current == "DevelopError":
            return "5xx"
        if current in seen:
            continue
        seen.add(current)
        stack.extend(bases.get(current, []))
    return None


def _layer(path: Path) -> str:
    parts = path.parts
    if "domain" in parts:
        return "domain"
    if "behavior" in parts:
        return "behavior"
    if "worker" in parts:
        return "worker"
    if "infrastructure" in parts:
        for adapter in ("hash", "notification", "database"):
            if adapter in parts:
                return adapter
        return "infrastructure"
    return "core"


# #
# raise sites

def _raises_in(node, registry: dict) -> list[str]:
    out = []
    for inner in ast.walk(node):
        if isinstance(inner, ast.Raise) and isinstance(inner.exc, ast.Call) \
                and isinstance(inner.exc.func, ast.Name):
            name = inner.exc.func.id
            if name in registry and registry[name]["code"] and name not in out:
                out.append(name)
    return out


def _vo_raises(registry: dict) -> dict:
    out = {}
    for path in _domain_files():
        for node in ast.walk(parse_source(path)):
            if isinstance(node, ast.ClassDef) \
                    and any(isinstance(b, ast.Name) and b.id == "ValueObject" for b in node.bases):
                out[node.name] = _raises_in(node, registry)
    return out


def _method_raises(registry: dict) -> dict:
    out = {}
    for path in _domain_files():
        for node in ast.walk(parse_source(path)):
            if not (isinstance(node, ast.ClassDef) and node.name.endswith("Repository")):
                continue
            for member in node.body:
                if isinstance(member, (ast.AsyncFunctionDef, ast.FunctionDef)) and not member.name.startswith("_"):
                    raises = _raises_in(member, registry)
                    if raises:
                        out[(node.name, member.name)] = raises
    return out


def _usecase_raises(registry: dict) -> dict:
    out = {}
    for path in _usecase_files():
        action = _action(parse_source(path))
        if action is not None:
            out[path.stem] = _raises_in(action, registry)
    return out


def _scope_raises(paths: list[Path], registry: dict) -> list[str]:
    out = []
    for path in paths:
        for name in _raises_in(parse_source(path), registry):
            if name not in out:
                out.append(name)
    return out


# #
# adapter

def _adapter_catalog(registry: dict) -> dict:
    root = _api_root() / "infrastructure"
    return {
        "db": _scope_raises([root / "database" / "common" / "session.py", root / "database" / "postgresql" / "repository.py"], registry),
        "hash": _scope_raises(_files(root / "hash"), registry),
        "notification": _scope_raises(_files(root / "notification"), registry),
    }


def _adapter_methods(registry: dict) -> dict:
    out = {}
    for adapter in ("hash", "notification"):
        for path in _files(_api_root() / "infrastructure" / adapter):
            tree = parse_source(path)
            classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
            method_raises = {name: _method_raise_map(node, registry) for name, node in classes.items()}
            for node in tree.body:
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) \
                        and isinstance(node.value.func, ast.Name) and node.value.func.id in classes:
                    raises = method_raises[node.value.func.id]
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            out[target.id] = {m: r for m, r in raises.items() if r and not m.startswith("_")}
    return out


def _method_raise_map(node: ast.ClassDef, registry: dict) -> dict:
    direct, calls = {}, {}
    for member in node.body:
        if isinstance(member, (ast.AsyncFunctionDef, ast.FunctionDef)):
            direct[member.name] = _raises_in(member, registry)
            calls[member.name] = _self_calls(member)
    return {name: _resolve_raises(name, direct, calls, set()) for name in direct}


def _self_calls(member) -> list[str]:
    out = []
    for inner in ast.walk(member):
        if isinstance(inner, ast.Attribute) and isinstance(inner.value, ast.Name) and inner.value.id == "self":
            out.append(inner.attr)
    return out


def _resolve_raises(name: str, direct: dict, calls: dict, seen: set) -> list[str]:
    if name in seen or name not in direct:
        return []
    seen.add(name)
    out = list(direct[name])
    for callee in calls.get(name, []):
        for raised in _resolve_raises(callee, direct, calls, seen):
            if raised not in out:
                out.append(raised)
    return out


def _usecase_adapter_calls(name: str, adapter_methods: dict) -> list[tuple]:
    path = _api_root() / "usecase" / f"{name}.py"
    if not path.exists():
        return []
    action = _action(parse_source(path))
    if action is None:
        return []
    out = []
    for node in ast.walk(action):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and isinstance(node.func.value, ast.Name) and node.func.value.id in adapter_methods:
            pair = (node.func.value.id, node.func.attr)
            if pair not in out:
                out.append(pair)
    return out


# #
# catalog

def _catalog() -> dict:
    path = _api_root() / "core" / "i18n.py"
    out = {}
    for node in ast.walk(parse_source(path)):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict) \
                and any(isinstance(t, ast.Name) and t.id == "_CATALOG" for t in node.targets):
            for key, value in zip(node.value.keys, node.value.values):
                if isinstance(key, ast.Constant) and isinstance(value, ast.Dict):
                    out[key.value] = _first_template(value)
    return out


def _first_template(value: ast.Dict) -> str:
    for entry in value.values:
        if isinstance(entry, ast.Constant) and isinstance(entry.value, str):
            return entry.value
    return ""


# #
# sources

def _api_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _files(directory: Path) -> list[Path]:
    return [
        path
        for path in sorted(directory.rglob("*.py"))
        if "__pycache__" not in str(path)
    ]


def _domain_files() -> list[Path]:
    return _files(_api_root() / "domain")


def _usecase_files() -> list[Path]:
    return [
        path
        for path in sorted((_api_root() / "usecase").glob("*.py"))
        if path.name != "__init__.py" and not path.name.startswith("_")
    ]


def _behavior_files() -> list[Path]:
    return _files(_api_root() / "behavior" / "context")


def _action(tree: ast.Module):
    for node in tree.body:
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) and not node.name.startswith("_"):
            return node
    return None
