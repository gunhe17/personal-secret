from __future__ import annotations

from sqlalchemy import text


# #
# row-level security — 테넌트 격리 백스톱
# team_id == current_setting('app.current_team') 일 때만 행 노출/삽입.
# current_team 미설정(outbox 워커 등 시스템 경로)이면 전체 허용.

_TENANT_TABLES = ("secrets", "events")

_PREDICATE = (
    "current_setting('app.current_team', true) IS NULL "
    "OR team_id = current_setting('app.current_team', true)::uuid"
)


def apply_rls(conn) -> None:
    for table in _TENANT_TABLES:
        conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        conn.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
        conn.execute(text(f"DROP POLICY IF EXISTS tenant_isolation ON {table}"))
        conn.execute(text(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING ({_PREDICATE}) WITH CHECK ({_PREDICATE})"
        ))
