from __future__ import annotations

from sqlalchemy import text


# #
# row-level security

TENANT_SETTING = "app.current_team"

_TENANT_COLUMNS = {
    "secrets": "team_id",
    "atomic_events": "actor_team_id",
}


def _predicate(column: str) -> str:
    # NULL setting ↔ NULL row 만 통과 — 미설정 시 전체 노출(fail-open) 차단, global(team 없는) 행은 NULL 컨텍스트 전용
    return f"{column} IS NOT DISTINCT FROM current_setting('{TENANT_SETTING}', true)::uuid"


def apply_rls(conn) -> None:
    for table, column in _TENANT_COLUMNS.items():
        predicate = _predicate(column)
        conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        conn.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
        conn.execute(text(f"DROP POLICY IF EXISTS tenant_isolation ON {table}"))
        conn.execute(text(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING ({predicate}) WITH CHECK ({predicate})"
        ))
