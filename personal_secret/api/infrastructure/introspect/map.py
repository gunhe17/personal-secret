from __future__ import annotations

import ast
import re
from pathlib import Path

from personal_secret.api.infrastructure.introspect.schema import build_schema


# #
# build — domain table 구조(schema) + usecase 흐름을 합친 설계 map

def build_map() -> dict:
    schema = build_schema()
    return {
        "tables": schema["tables"],
        "rels": schema["rels"],
        "usecases": build_usecases(),
    }


# #
# usecase — usecase/*.py 를 읽어 입력·흐름·의존 repository 추출
# flow 는 본문 # label 단계 마커 순서(find → persist → return …)

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

    # action (모듈 최상위 public 함수 — 없으면 usecase 아님)
    action = _action_def(tree)
    if action is None:
        return None

    name = path.stem
    body = source.splitlines()[action.lineno - 1 : action.end_lineno]
    usecase = {
        "name": name,
        "aggregate": (
            name[: -len(action.name) - 1] if name.endswith(action.name) else name
        ),
        "action": action.name,
        "input": _input_fields(tree),
        "flow": _flow_steps(body),
        "repositories": _repositories(body),
    }
    return usecase


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


def _flow_steps(body: list[str]) -> list[str]:
    return [
        match.group(1)
        for line in body
        if (match := _STEP.match(line))
    ]


def _repositories(body: list[str]) -> list[str]:
    seen = []
    for line in body:
        for name in _REPOSITORY.findall(line):
            if name not in seen:
                seen.append(name)
    return seen
