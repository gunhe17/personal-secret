from __future__ import annotations

import ast
from pathlib import Path


# #
# repo → table

def build_repo_tables() -> dict:
    directory = (
        Path(__file__)
        .resolve()
        .parent.parent.parent / "domain"
    )
    out = {}
    for path in sorted(directory.rglob("*_repository.py")):
        tree = ast.parse(path.read_text())
        model_table = {
            node.name: _tablename(node)
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and _tablename(node)
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.endswith("Repository"):
                for base in node.bases:
                    model = _base_model(base)
                    if model in model_table:
                        out[node.name] = model_table[model]
    return out


def _tablename(node: ast.ClassDef) -> str | None:
    for stmt in node.body:
        if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Constant) \
                and any(isinstance(t, ast.Name) and t.id == "__tablename__" for t in stmt.targets):
            return str(stmt.value.value)
    return None


def _base_model(base) -> str | None:
    if not isinstance(base, ast.Subscript):
        return None
    sliced = base.slice
    elements = sliced.elts if isinstance(sliced, ast.Tuple) else [sliced]
    names = [e.id for e in elements if isinstance(e, ast.Name)]
    return names[-1] if names else None


# #
# repository

# SELECT 판별은 메서드명이 아니라 _find/_filter 류 read helper 호출 여부로 한다
_READ_HELPERS = {"_find", "_filter", "_find_by", "_filter_by", "_filter_by_all", "_exists_by", "_count"}
_WRITE_PREFIX = ("_add", "_update", "_remove", "_upsert", "_set", "_delete", "_create")


def build_repositories() -> list[dict]:
    directory = (
        Path(__file__)
        .resolve()
        .parent.parent.parent / "domain"
    )
    base = _base_facts()
    out = []
    for path in sorted(directory.rglob("*_repository.py")):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.endswith("Repository"):
                out.extend(_repo_queries(node, base))
    return out


# 베이스 클래스 PostgresRepository 메서드를 concrete 가 override 안 하면 delegation 으로 상속하므로, 베이스 사실도 fallback 으로 모아둔다
def _base_facts() -> dict:
    base_path = (
        Path(__file__)
        .resolve()
        .parent.parent / "database" / "postgresql" / "repository.py"
    )
    if not base_path.exists():
        return {}
    tree = ast.parse(base_path.read_text())
    return {
        m.name: _method_facts(m)
        for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
        for m in node.body
        if isinstance(m, (ast.AsyncFunctionDef, ast.FunctionDef)) and not m.name.startswith("_")
    }


def _dedup(items: list) -> list:
    out = []
    for x in items:
        if x not in out:
            out.append(x)
    return out


def _model_cols(node) -> list[str]:
    cols = []
    for inner in ast.walk(node):
        # Model.col == value
        if isinstance(inner, ast.Compare) and isinstance(inner.left, ast.Attribute) \
                and isinstance(inner.left.value, ast.Name) and inner.left.value.id.endswith("Model"):
            cols.append(inner.left.attr)
        # Model.col.in_(...) 등
        if isinstance(inner, ast.Attribute) and isinstance(inner.value, ast.Attribute) \
                and isinstance(inner.value.value, ast.Name) and inner.value.value.id.endswith("Model"):
            cols.append(inner.value.attr)
    return cols


def _method_facts(m) -> dict:
    card = _cardinality(getattr(m, "returns", None))
    args = [a.arg for a in m.args.args] + [a.arg for a in m.args.kwonlyargs]
    paginated = "limit" in args or "offset" in args

    where, order_by, calls = [], None, set()
    direct_query = has_write = False
    optional = set()

    for node in ast.walk(m):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            fn, owner = node.func.attr, node.func.value
            if isinstance(owner, ast.Name) and owner.id == "cls":
                if fn in _READ_HELPERS:
                    direct_query = True
                elif fn.startswith(_WRITE_PREFIX):
                    has_write = True
                else:
                    calls.add(fn)
                for kw in node.keywords:
                    if kw.arg == "column" and isinstance(kw.value, ast.Constant):
                        where.append(kw.value.value)
                    if kw.arg == "order_by" and isinstance(kw.value, ast.Constant):
                        order_by = kw.value.value
            if isinstance(owner, ast.Name) and owner.id == "session" and fn in ("add", "execute", "delete"):
                has_write = True
            if fn == "append":
                for c in _model_cols(node):
                    optional.add(c)
        if isinstance(node, ast.If):
            for c in _model_cols(node):
                optional.add(c)

    cols = _model_cols(m)
    where += [c for c in cols if c not in optional]
    return {
        "card": card, "paginated": paginated, "order_by": order_by,
        "where": _dedup(where), "opt_where": _dedup([c for c in cols if c in optional]),
        "calls": calls, "direct_query": direct_query, "has_write": has_write,
    }


def _cardinality(returns) -> str:
    if returns is None:
        return "one"
    txt = ast.unparse(returns)
    if "list[" in txt or "Sequence[" in txt:
        return "many"
    if txt == "bool":
        return "exists"
    return "one"


def _resolve(name: str, raw: dict, seen: set) -> dict:
    base = {"is_query": False, "has_write": False, "where": [], "opt_where": [], "order_by": None, "paginated": False}
    if name in seen or name not in raw:
        return base
    seen.add(name)
    f = raw[name]
    res = {
        "is_query": f["direct_query"], "has_write": f["has_write"],
        "where": list(f["where"]), "opt_where": list(f["opt_where"]),
        "order_by": f["order_by"], "paginated": f["paginated"],
    }
    for callee in f["calls"]:
        r = _resolve(callee, raw, seen)
        res["has_write"] = res["has_write"] or r["has_write"]   # write 를 delegation 따라 전파
        if r["is_query"]:
            res["is_query"] = True
            res["where"] = _dedup(res["where"] + r["where"])
            res["opt_where"] = _dedup(res["opt_where"] + r["opt_where"])
            res["order_by"] = res["order_by"] or r["order_by"]
            res["paginated"] = res["paginated"] or r["paginated"]
    return res


def _repo_queries(cls_node, base: dict) -> list[dict]:
    raw = {
        m.name: _method_facts(m)
        for m in cls_node.body
        if isinstance(m, (ast.AsyncFunctionDef, ast.FunctionDef)) and not m.name.startswith("_")
    }
    lookup = {**base, **raw}   # concrete 가 base 를 override
    out = []
    for name, f in raw.items():
        resolved = _resolve(name, dict(lookup), set())
        if resolved["has_write"] or not resolved["is_query"]:
            continue
        opt = [c for c in resolved["opt_where"] if c not in resolved["where"]]
        out.append({
            "repo": cls_node.name, "method": name, "card": f["card"],
            "where": resolved["where"], "opt_where": opt,
            "order_by": resolved["order_by"], "paginated": resolved["paginated"],
        })
    return out
