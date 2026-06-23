"""AST 기반 의존성 분석 — 양방향.

dependents:    이 파일에 의존하는 것들 (역참조 — 누가 나를 import하나)
dependencies:  이 파일이 의존하는 내부(api) 것들 (순참조 — 내가 무엇을 import하나) + 레이어 방향(INV-1) 위반 플래그
"""
from __future__ import annotations

import ast
from pathlib import Path


# #
# tool

# 레이어 rank. 높을수록 상위, 상위는 하위만 import 가능하고 core(0)는 누구나 가능하다. api.md [INV-1] 참고
RANK = {
    "bin": 6,
    "server": 5,
    "endpoint": 4,
    "usecase": 3,
    "domain": 2,
    "infrastructure": 1,
    "core": 0,
}
PREFIX = "personal_secret.api."

# `import personal_secret.api.domain` 은 SQLAlchemy 가 모든 Model 을 Base.metadata 에 올리도록 하는 idiom. 도메인 로직 의존이 아니라 위반도 아니다. api.md [INV-1] 참고
REGISTRATION_IMPORT = "personal_secret.api.domain"


class Dependency:
    def dependents(self, *, file: str, name: str | None = None, root: str | None = None) -> dict:
        file_path = Path(file)
        root_path = Path(root) if root else None
        base = (root_path or self._default_root()).resolve()
        hits = self._find_usages(file_path, name, root_path)
        dependents = []
        for path, line in hits:
            rel = path.relative_to(base) if path.is_relative_to(base) else path
            dependents.append(f"{rel}:{line}")
        return {"dependents": dependents}

    def dependencies(self, *, file: str, root: str | None = None) -> dict:
        path = Path(file)
        source_layer = self._layer_of_path(path)
        if source_layer not in RANK or not str(path).endswith(".py"):
            return {"source_layer": None, "dependencies": []}
        if "/personal_secret/api/" not in str(path).replace("\\", "/"):
            return {"source_layer": None, "dependencies": []}
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError):
            return {"source_layer": source_layer, "dependencies": []}

        dependencies = [
            {
                "module": module,
                "target_layer": target,
                "violation": RANK[target] > RANK[source_layer] and not registration,
            }
            for module, target, registration in self._internal_imports(tree)
        ]
        return {"source_layer": source_layer, "dependencies": dependencies}

    def _find_usages(
        self,
        file: Path,
        name: str | None = None,
        root: Path | None = None,
    ) -> list[tuple[Path, int]]:
        file = file.resolve()
        root = (root or self._default_root()).resolve()
        rel = file.relative_to(root)

        parts = list(rel.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        candidates = {".".join(parts[i:]) for i in range(len(parts))}

        hits: list[tuple[Path, int]] = []
        for path in root.rglob("*.py"):
            if path.resolve() == file:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module not in candidates:
                        continue
                    if name is None:
                        hits.append((path, node.lineno))
                    else:
                        for alias in node.names:
                            if alias.name == name:
                                hits.append((path, node.lineno))
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in candidates:
                            hits.append((path, node.lineno))
        return hits

    def _internal_imports(self, tree: ast.AST) -> list[tuple[str, str, bool]]:
        found = []
        for node in ast.walk(tree):
            entries = []
            if isinstance(node, ast.ImportFrom):
                entries.append((node.module, False))
            elif isinstance(node, ast.Import):
                entries.extend((alias.name, alias.name == REGISTRATION_IMPORT) for alias in node.names)
            for module, registration in entries:
                target = self._layer_of_module(module)
                if target in RANK:
                    found.append((module, target, registration))
        return found

    def _default_root(self) -> Path:
        here = Path(__file__).resolve()
        for parent in [here, *here.parents]:
            if (parent / "pyproject.toml").exists():
                return parent
        return Path.cwd()

    def _layer_of_path(self, path: Path) -> str | None:
        parts = str(path).replace("\\", "/").split("/")
        if "api" not in parts:
            return None
        i = parts.index("api")
        return parts[i + 1] if i + 1 < len(parts) else None

    def _layer_of_module(self, module: str | None) -> str | None:
        if not module or not module.startswith(PREFIX):
            return None
        rest = module[len(PREFIX):]
        return rest.split(".")[0] if rest else None


# #
# Dependency

dependency = Dependency()
