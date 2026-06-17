"""PostToolUse 훅 — 편집으로 새로 들어온 텍스트에 '라벨 뒤 괄호 부연'이 있으면 경고.

conventions.md:398 ("라벨 뒤 한국어 부연 — why/계약/주의만, what 재서술 금지")을 기계적으로
잡는다. 새로 추가된 줄(Edit: new_string, Write: content)만 검사해 기존 줄 재경고를 피한다.
판정은 휴리스틱(형태만 본다) — 정당한 why/계약/함정 부연에도 걸릴 수 있으니, 경고는 차단이
아니라 "정당화 아니면 지워라" 환기다. 실패는 조용히 통과(exit 0), 감지 시에만 exit 2.
"""
from __future__ import annotations

import json
import re
import sys


# #
# detect

# 줄 전체가 라벨 주석이고 라벨 뒤에 ` (...` 괄호 부연이 붙은 형태:
#   "# plain (..."  "    # emit (..."  "# command (require_member ..."
# "# #" 섹션 시길은 라벨이 소문자로 시작 안 하므로 비매칭.
LABEL_PAREN = re.compile(r"^\s*#\s+[a-z][\w ]*\s+\(")


def label_paren_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if LABEL_PAREN.match(line)]


# #
# run

def run() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return 0

    tool_input = payload.get("tool_input") or {}
    path = tool_input.get("file_path", "")
    if not path.endswith(".py"):
        return 0

    added = tool_input.get("new_string") or tool_input.get("content") or ""
    removed = set(label_paren_lines(tool_input.get("old_string") or ""))
    flagged = [line for line in label_paren_lines(added) if line not in removed]
    if not flagged:
        return 0

    lines = ["[주석] 라벨 뒤 괄호 부연 감지 — conventions.md:398 (why/계약/함정만, what 재서술 금지):"]
    lines += [f"  {line}" for line in flagged]
    lines.append("코드·시그니처·타입·docs에 이미 있는 정보면 괄호째 지우고 라벨만 남겨라.")
    sys.stderr.write("\n".join(lines) + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(run())
