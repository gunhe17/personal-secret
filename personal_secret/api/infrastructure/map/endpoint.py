from __future__ import annotations

import ast
import re
from pathlib import Path

from personal_secret.api.infrastructure.map.source import parse_source
from personal_secret.api.infrastructure.map.usecase import build_usecases


# #
# endpoint

def build_endpoints(usecases: list[dict] | None = None) -> list[dict]:
    bin_path = (
        Path(__file__)
        .resolve()
        .parent.parent.parent / "bin" / "server.py"
    )
    tree = parse_source(bin_path)
    routes = [
        route
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Router"
        if (route := _route(node))
    ]
    handler_usecase = _handler_usecases()
    by_name = {uc["name"]: uc for uc in (usecases if usecases is not None else build_usecases())}
    for route in routes:
        usecase = handler_usecase.get(route["handler"])
        route["usecase"] = usecase
        module, func = route["handler"].split(".", 1)
        inputs, field_map, auth = _endpoint_io(module, func, route["path"], usecase, by_name.get(usecase))
        route["inputs"] = inputs
        route["field_map"] = field_map
        route["auth"] = auth
    return routes


def _route(call: ast.Call) -> dict | None:
    path = method = handler = None
    for kw in call.keywords:
        if kw.arg == "path" and isinstance(kw.value, ast.Constant):
            path = kw.value.value
        elif kw.arg == "methods" and isinstance(kw.value, ast.List):
            methods = [e.value for e in kw.value.elts if isinstance(e, ast.Constant)]
            method = methods[0] if methods else None
        elif kw.arg == "endpoint" and isinstance(kw.value, ast.Attribute) \
                and isinstance(kw.value.value, ast.Name):
            handler = f"{kw.value.value.id}.{kw.value.attr}"
    if not (path and method and handler):
        return None
    return {"method": method, "path": path, "handler": handler}


def _handler_usecases() -> dict:
    directory = (
        Path(__file__)
        .resolve()
        .parent.parent.parent / "endpoint"
    )
    out = {}
    for path in sorted(directory.glob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = parse_source(path)
        modules = _usecase_imports(tree)
        for node in tree.body:
            if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) and not node.name.startswith("_"):
                out[f"{path.stem}.{node.name}"] = _usecase_call(node, modules)
    return out


def _usecase_imports(tree: ast.Module) -> set:
    out = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "personal_secret.api.usecase":
            for alias in node.names:
                out.add(alias.asname or alias.name)
    return out


def _usecase_call(func, modules: set) -> str | None:
    for node in ast.walk(func):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and isinstance(node.func.value, ast.Name) and node.func.value.id in modules:
            return node.func.value.id
    return None


def _endpoint_io(module: str, func_name: str, path: str, usecase: str | None, uc: dict | None) -> tuple[list, dict, str | None]:
    directory = (
        Path(__file__)
        .resolve()
        .parent.parent.parent / "endpoint"
    )
    tree = parse_source(directory / f"{module}.py")
    func = next(
        (n for n in tree.body if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef)) and n.name == func_name),
        None,
    )
    if func is None:
        return [], {}, None

    path_params = set(re.findall(r"\{(\w+)\}", path))
    vo = {validation["field"]: validation["vo"] for validation in (uc["validations"] if uc else [])}
    defaults = _arg_defaults(func.args)

    inputs, body_fields = [], []
    for arg in func.args.posonlyargs + func.args.args + func.args.kwonlyargs:
        name = arg.arg
        if name in ("self", "cls") or _is_depends(defaults.get(name)):
            continue
        annotation = ast.unparse(arg.annotation) if arg.annotation else None
        if name in path_params:
            inputs.append({"name": name, "kind": "path", "type": annotation})
        elif annotation and annotation.endswith(".Input"):
            for field in (uc["input"] if uc else []):
                inputs.append({"name": field, "kind": "body", "type": vo.get(field)})
                body_fields.append(field)
        elif annotation and _local_model(tree, annotation):
            for field in _local_model_fields(tree, annotation):
                inputs.append({"name": field, "kind": "body", "type": None})
                body_fields.append(field)
        else:
            inputs.append({"name": name, "kind": "query", "type": annotation})

    field_map = _field_map(_input_arg(func, usecase), body_fields)
    return inputs, field_map, _handler_auth(defaults)


def _handler_auth(defaults: dict) -> str | None:
    for name, default in defaults.items():
        if "session" not in name or not _is_depends(default):
            continue
        dep = default.args[0] if default.args else None
        dep_name = dep.id if isinstance(dep, ast.Name) else None
        if not dep_name:
            return None
        for level in ("owner", "team", "account"):
            if f"authenticated_{level}" in dep_name:
                return level
        return "none"
    return None


def _arg_defaults(args: ast.arguments) -> dict:
    out = {}
    positional = args.posonlyargs + args.args
    for arg, default in zip(positional[len(positional) - len(args.defaults):], args.defaults):
        out[arg.arg] = default
    for arg, default in zip(args.kwonlyargs, args.kw_defaults):
        if default is not None:
            out[arg.arg] = default
    return out


def _is_depends(node) -> bool:
    return isinstance(node, ast.Call) and (
        (isinstance(node.func, ast.Name) and node.func.id == "Depends")
        or (isinstance(node.func, ast.Attribute) and node.func.attr == "Depends")
    )


def _local_model(tree: ast.Module, name: str) -> bool:
    return any(isinstance(node, ast.ClassDef) and node.name == name for node in tree.body)


def _local_model_fields(tree: ast.Module, name: str) -> list[str]:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return [
                statement.target.id
                for statement in node.body
                if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)
            ]
    return []


def _input_arg(func, usecase: str | None):
    for node in ast.walk(func):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and isinstance(node.func.value, ast.Name) and node.func.value.id == usecase:
            for kw in node.keywords:
                if kw.arg == "input":
                    return kw.value
    return None


def _field_map(input_arg, body_fields: list) -> dict:
    if isinstance(input_arg, ast.Name):
        return {field: field for field in body_fields}
    if isinstance(input_arg, ast.Call):
        out = {}
        for kw in input_arg.keywords:
            leaf = _leaf_name(kw.value) if kw.arg else None
            if kw.arg and leaf:
                out[kw.arg] = leaf
        return out
    return {}


def _leaf_name(node) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    for inner in ast.walk(node):
        if isinstance(inner, ast.Name) and inner.id not in ("str", "UUID", "int", "bytes", "float"):
            return inner.id
    return None
