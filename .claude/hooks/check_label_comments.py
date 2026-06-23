"""PostToolUse 훅 — 편집으로 새로 들어온 텍스트에 '라벨 뒤 부연' 또는 '선언 위 산문 주석'을 경고.

conventions.md:398 ("라벨 뒤 한국어 부연 — why/계약/주의만, what 재서술 금지")을 기계적으로
잡는다. 새로 추가된 줄(Edit: new_string, Write: content)만 검사해 기존 줄 재경고를 피한다.

잡는 형태 셋 (what 재서술의 흔한 그릇):
  소문자 라벨 + 괄호:   '# emit (actor 없음)',  '# command (require_member ...)'
  em-dash 부연:         '# input — ... 자족',   '# 공급된 경우만 — 미공급'
  선언 바로 위 산문:     '# 초대받는이 ... ciphertext' 다음 줄이 'team_locked_key: str'
선언 contract 가 진짜 필요하면 별도 줄이 아니라 선언 줄 끝 '트레일링 인라인' 으로
('field: str  # 초대받는이 ... ciphertext') — 트레일링 주석은 줄머리가 '#' 이 아니라 통과한다.
'# #' 섹션·단일 라벨('# hint')·스코프 태그('# TODO(infra)') 는 비매칭.

판정은 휴리스틱(형태만 본다) — 정당한 why/계약 부연에도 걸릴 수 있으니, 경고는 차단이 아니라
"정당화면 트레일링 인라인, 아니면 지워라" 환기다. 실패는 조용히 통과(exit 0), 감지 시 exit 2.

(예시 문자열은 '#' 주석이 아니라 이 docstring 안에 둔다 — 정규식은 줄머리 '#' 만 보므로 자기-플래그 회피.)
"""
from __future__ import annotations

import json
import re
import sys


# #
# detect

ADDENDUM = re.compile(r"^\s*#\s+(?:[a-z].*\(|(?!#).*—)")   # 라벨 뒤 괄호·em-dash 부연
PROSE = re.compile(r"^\s*#\s+\S+\s+\S")                    # # 다음 2토큰+ = 산문(단일 라벨 제외)
DECL = re.compile(r"^\s*[A-Za-z_]\w*\s*:")                 # name: type 선언


def _next_code(lines: list[str], i: int) -> str:
    for line in lines[i + 1:]:
        if line.strip():
            return line
    return ""


def flagged_lines(text: str) -> list[str]:
    lines = text.splitlines()
    out = []
    for i, line in enumerate(lines):
        if ADDENDUM.match(line):
            out.append(line.strip())
        elif PROSE.match(line) and DECL.match(_next_code(lines, i)):
            out.append(line.strip())
    return out


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
    removed = set(flagged_lines(tool_input.get("old_string") or ""))
    flagged = [line for line in flagged_lines(added) if line not in removed]
    if not flagged:
        return 0

    lines = ["[주석] 라벨 뒤 부연(괄호·em-dash) 또는 선언 위 산문 주석 감지 — conventions.md:398:"]
    lines += [f"  {line}" for line in flagged]
    lines.append("정당한 계약이면 선언 줄 끝 트레일링 인라인으로, 아니면 지워라. 라벨만 남기는 게 기본.")
    sys.stderr.write("\n".join(lines) + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(run())
