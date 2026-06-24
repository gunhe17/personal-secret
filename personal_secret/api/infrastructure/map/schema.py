from __future__ import annotations

from sqlalchemy import UniqueConstraint

import personal_secret.api.domain  # noqa: F401  (모든 Model 을 metadata 에 등록)
from personal_secret.api.core.model import Base


# #
# schema

# FK 는 미선언(raw UUID)이라 컬럼 컨벤션으로 추론: {x}_id → {x}s

def build_schema() -> dict:
    names = set(Base.metadata.tables.keys())
    tables = []
    for table_name, table in sorted(Base.metadata.tables.items()):
        single_unique, composite_unique = _uniques(table)
        columns = [
            {
                "name": column.name,
                "type": column.type.__class__.__name__,
                "pk": column.primary_key,
                "nullable": column.nullable,
                "unique": column.name in single_unique,
                "fk": _fk_target(column.name, names),
            }
            for column in table.columns
        ]
        tables.append({
            "name": table_name,
            "columns": columns,
            "composite_unique": composite_unique,
        })

    rels = [
        {"from": t["name"], "col": c["name"], "to": c["fk"]}
        for t in tables for c in t["columns"] if c["fk"]
    ]
    return {"tables": tables, "rels": rels}


def _uniques(table) -> tuple[set, list]:
    single, composite = set(), []
    for source in [c for c in table.constraints if isinstance(c, UniqueConstraint)] + [i for i in table.indexes if i.unique]:
        cols = [column.name for column in source.columns]
        if len(cols) == 1:
            single.add(cols[0])
        elif cols:
            composite.append(cols)
    return single, composite


def _fk_target(column_name: str, table_names: set) -> str | None:
    if column_name.endswith("_id") and column_name != "id":
        candidate = column_name[:-3] + "s"
        if candidate in table_names:
            return candidate
    return None
