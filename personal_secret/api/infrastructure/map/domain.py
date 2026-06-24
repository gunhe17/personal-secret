from __future__ import annotations

import ast
from functools import lru_cache
from pathlib import Path

from personal_secret.api.infrastructure.map.source import parse_source


# #
# domain reference

def _domain_classes(base: str):
    for node, tree in _domain_defs(_domain_signature()):
        if any(isinstance(b, ast.Name) and b.id == base for b in node.bases):
            yield node, tree


def _domain_signature() -> tuple:
    directory = (
        Path(__file__)
        .resolve()
        .parent.parent.parent / "domain"
    )
    return tuple(
        (str(path), path.stat().st_mtime)
        for path in sorted(directory.rglob("*.py"))
        if "__pycache__" not in str(path)
    )


# 한 build 의 3개 빌더가 도메인 파일을 한 번만 walk 하도록 signature 로 캐시
@lru_cache(maxsize=None)
def _domain_defs(signature: tuple) -> list:
    out = []
    for path, _ in signature:
        tree = parse_source(Path(path))
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                out.append((node, tree))
    return out


def _literal(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.Tuple, ast.List)):
        return [
            element.value if isinstance(element, ast.Constant) else element.id
            for element in node.elts
            if isinstance(element, (ast.Constant, ast.Name))
        ]
    return None


def build_value_objects() -> list[dict]:
    out = []
    for node, _ in _domain_classes("ValueObject"):
        value_type, rules = None, {}
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                name = stmt.target.id
                if name == "_value":
                    value_type = ast.unparse(stmt.annotation)
                elif name.startswith("_") and stmt.value is not None:
                    literal = _literal(stmt.value)
                    if literal is not None:
                        rules[name.lstrip("_")] = literal
        out.append({"name": node.name, "type": value_type, "rules": rules})
    return out


def build_entities() -> list[dict]:
    out = []
    for node, _ in _domain_classes("Entity"):
        fields = [
            {"name": stmt.target.id, "type": ast.unparse(stmt.annotation)}
            for stmt in node.body
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and not stmt.target.id.startswith("_")
        ]
        out.append({"name": node.name, "fields": fields})
    return out


def build_events() -> list[dict]:
    out = []
    for node, tree in _domain_classes("Event"):
        out.append({
            "name": node.name,
            "entity": _method_const(node, "act_entity_name"),
            "kinds": _event_kinds(node, tree),
            "payload": _payload_keys(node),
        })
    return out


def _method_const(node: ast.ClassDef, name: str):
    for member in node.body:
        if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and member.name == name:
            for inner in ast.walk(member):
                if isinstance(inner, ast.Return) and isinstance(inner.value, ast.Constant):
                    return inner.value.value
    return None


def _event_kinds(node: ast.ClassDef, tree: ast.Module) -> list:
    kind_type = next(
        (ast.unparse(s.annotation) for s in node.body
         if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name) and s.target.id == "_kind"),
        None,
    )
    if not kind_type:
        return []
    for n in tree.body:
        if isinstance(n, ast.ClassDef) and n.name == kind_type:
            return [a.value.value for a in n.body if isinstance(a, ast.Assign) and isinstance(a.value, ast.Constant)]
    return []


def _payload_keys(node: ast.ClassDef) -> list:
    for member in node.body:
        if isinstance(member, ast.FunctionDef) and member.name == "payload":
            keys = set()
            for inner in ast.walk(member):
                if isinstance(inner, ast.Dict):
                    keys.update(k.value for k in inner.keys if isinstance(k, ast.Constant))
                if isinstance(inner, ast.Subscript) and isinstance(inner.slice, ast.Constant):
                    keys.add(inner.slice.value)
            return sorted(keys)
    return []
