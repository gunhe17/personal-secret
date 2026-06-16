"""PostToolUse 훅 — 편집한 .py 의 레이어 의존 방향(INV-1)을 MCP 로 검사.

검사 로직은 MCP 도구(`show_dependencies`, personal_secret/mcp/tools/dependency)가 단일 소유.
훅은 실행 중 mcp 컨테이너에 HTTP 로 위임만 한다. MCP 미가동·미설치·타임아웃 등
모든 실패는 편집을 막지 않도록 조용히 통과(exit 0), 실제 위반일 때만 exit 2.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys


TIMEOUT_SEC = 5.0


# #
# call

async def fetch_dependencies(url: str, file: str) -> dict:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("show_dependencies", {"file": file})

    data = result.structuredContent
    if not data and result.content:
        text = getattr(result.content[0], "text", "")
        data = json.loads(text) if text else {}
    data = data or {}
    if "dependencies" not in data and isinstance(data.get("result"), dict):
        data = data["result"]
    return data


# #
# run

def run() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return 0

    path = (payload.get("tool_input") or {}).get("file_path", "")
    normalized = path.replace("\\", "/")
    if not path.endswith(".py") or "/personal_secret/api/" not in normalized:
        return 0

    port = os.environ.get("DEVELOP_MCP_CONTAINER_PORT")
    if not port:
        return 0
    url = f"http://mcp:{port}/mcp"

    try:
        data = asyncio.run(
            asyncio.wait_for(fetch_dependencies(url, path), TIMEOUT_SEC)
        )
    except Exception:
        # MCP 미가동·미설치·타임아웃 — 편집 차단하지 않음
        return 0

    source_layer = data.get("source_layer")
    violations = [d for d in (data.get("dependencies") or []) if d.get("violation")]
    if not violations:
        return 0

    lines = [
        f"[INV-1] 의존 방향 위반 — {source_layer} 레이어가 상위 {v['target_layer']} 를 import: {v['module']}"
        for v in violations
    ]
    lines.append("위→아래 import만 허용(모두 →core). personal_secret/api/CLAUDE.md [INV-1] 참고.")
    sys.stderr.write("\n".join(lines) + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(run())
