from __future__ import annotations

import ast
from functools import lru_cache
from pathlib import Path


# #
# source

def read_source(path: Path) -> str:
    return _read(str(path), path.stat().st_mtime)


def parse_source(path: Path) -> ast.Module:
    return _parse(str(path), path.stat().st_mtime)


# mtime 키라 파일 수정 시 자동 무효화. AST 는 read-only 로만 소비
@lru_cache(maxsize=None)
def _read(path: str, mtime: float) -> str:
    return Path(path).read_text()


@lru_cache(maxsize=None)
def _parse(path: str, mtime: float) -> ast.Module:
    return ast.parse(_read(path, mtime))
