from __future__ import annotations

from sqlalchemy import text


# #
# row-level security — 테넌트 격리 백스톱
# {테넌트 컬럼} == current_setting('app.current_team') 일 때만 행 노출/삽입.
# current_team 미설정(시스템 경로)이면 전체 허용.

# 테이블별 테넌트 컬럼 — secrets 는 team_id, events 는 actor_team_id(행위 팀)
_TENANT_COLUMNS = {
    "secrets": "team_id",
    "events": "actor_team_id",
}


def _predicate(column: str) -> str:
    return (
        "current_setting('app.current_team', true) IS NULL "
        f"OR {column} = current_setting('app.current_team', true)::uuid"
    )


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
