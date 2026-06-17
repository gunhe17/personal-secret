"""PostToolUse 훅 — 편집한 .py 의 레이어 의존 방향(INV-1)을 MCP 로 검사해 위반을 컨텍스트에 주입.

목적: LLM 이 직접 grep/CLI 로 의존성을 뒤지지 않고 MCP(`show_dependencies`)를 무조건 거치게 강제.
검사 로직은 MCP 도구(personal_secret/mcp/tools/dependency)가 단일 소유. 훅은 HTTP 위임만.
차단하지 않는다 — 위반을 알려주고 LLM 이 수정에 반영하게 한다(항상 exit 0). 위반 없으면 침묵.
MCP 미가동·미설치·타임아웃 등 모든 실패는 조용히 통과.
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
        # MCP 미가동·미설치·타임아웃 — 주입 없이 통과
        return 0

    source_layer = data.get("source_layer")
    violations = [d for d in (data.get("dependencies") or []) if d.get("violation")]
    if not violations:
        return 0

    lines = [
        f"[INV-1] 의존 방향 위반 — {source_layer} 레이어가 상위 {v['target_layer']} 를 import: {v['module']}"
        for v in violations
    ]
    lines.append("위→아래 import만 허용(모두 →core). 위반 import 를 제거하거나 의존을 뒤집어라. personal_secret/api/CLAUDE.md [INV-1] 참고.")

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": "\n".join(lines),
        }
    }
    sys.stdout.write(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(run())
