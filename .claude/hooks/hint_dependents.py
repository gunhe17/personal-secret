"""PreToolUse 훅 — 편집할 .py 의 dependents(역참조, 누가 나를 import하나)를 MCP 로 조회해
모델 컨텍스트에 주입. blast radius 를 손으로 떠올릴 필요 없게 만든다(트리거 마찰 제거).

검사 로직은 MCP 도구(`show_dependents`, personal_secret/mcp/tools/dependency)가 단일 소유.
훅은 실행 중 mcp 컨테이너에 HTTP 로 위임만 한다. 차단하지 않는다 — 정보 주입 전용(항상 exit 0).
MCP 미가동·미설치·타임아웃 등 모든 실패는 조용히 통과. 세션당 같은 파일은 1회만 주입(dedup).
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path


TIMEOUT_SEC = 5.0
CAP = 30


# #
# call

async def fetch_dependents(url: str, file: str) -> dict:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("show_dependents", {"file": file})

    data = result.structuredContent
    if not data and result.content:
        text = getattr(result.content[0], "text", "")
        data = json.loads(text) if text else {}
    data = data or {}
    if "dependents" not in data and isinstance(data.get("result"), dict):
        data = data["result"]
    return data


# #
# dedup

def already_hinted(session_id: str, path: str) -> bool:
    # 세션당 파일 1회 — 같은 파일 반복 편집 시 blast radius 덤프 반복 방지
    marker_dir = Path(tempfile.gettempdir()) / f"ps_dependents_{session_id or 'nosession'}"
    marker_dir.mkdir(parents=True, exist_ok=True)
    marker = marker_dir / hashlib.md5(path.encode()).hexdigest()
    if marker.exists():
        return True
    marker.touch()
    return False


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

    if already_hinted(payload.get("session_id", ""), path):
        return 0

    port = os.environ.get("DEVELOP_MCP_CONTAINER_PORT")
    if not port:
        return 0
    url = f"http://mcp:{port}/mcp"

    try:
        data = asyncio.run(
            asyncio.wait_for(fetch_dependents(url, path), TIMEOUT_SEC)
        )
    except Exception:
        # MCP 미가동·미설치·타임아웃 — 주입 없이 통과
        return 0

    dependents = data.get("dependents") or []
    if not dependents:
        return 0

    shown = dependents[:CAP]
    lines = [f"[blast radius] {os.path.basename(path)} 를 import하는 곳 {len(dependents)}개 — 수정 시 함께 반영:"]
    lines.extend(f"  - {d}" for d in shown)
    if len(dependents) > CAP:
        lines.append(f"  ... 외 {len(dependents) - CAP}개")

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": "\n".join(lines),
        }
    }
    sys.stdout.write(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(run())
