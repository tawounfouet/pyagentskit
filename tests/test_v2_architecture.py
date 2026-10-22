from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1] / "src" / "pyagentskit"


def _resolved_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    relative = path.relative_to(ROOT)
    package_parts = ["pyagentskit", *relative.parent.parts]
    imported: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level == 0:
                imported.add(module)
                continue
            keep = len(package_parts) - (node.level - 1)
            base = package_parts[: max(1, keep)]
            if module:
                base.extend(module.split("."))
            imported.add(".".join(base))
    return imported


def _imports_forbidden(imported: set[str], forbidden: set[str]) -> set[str]:
    return {
        name
        for name in imported
        if any(name == blocked or name.startswith(f"{blocked}.") for blocked in forbidden)
    }


class V2ArchitectureTests(unittest.TestCase):
    def test_domain_dependency_direction_is_inward_only(self) -> None:
        forbidden = {
            "pyagentskit.adapters",
            "pyagentskit.api",
            "pyagentskit.application",
            "pyagentskit.bootstrap",
            "pyagentskit.compat",
            "pyagentskit.postgres",
            "pyagentskit.postgres_state",
            "pyagentskit.providers",
        }

        for path in (ROOT / "domain").rglob("*.py"):
            violations = _imports_forbidden(_resolved_imports(path), forbidden)
            self.assertFalse(violations, f"{path}: forbidden imports {sorted(violations)}")

    def test_application_does_not_import_concrete_adapters_or_providers(self) -> None:
        forbidden = {
            "pyagentskit.adapters",
            "pyagentskit.providers",
        }

        for path in (ROOT / "application").rglob("*.py"):
            violations = _imports_forbidden(_resolved_imports(path), forbidden)
            self.assertFalse(violations, f"{path}: forbidden imports {sorted(violations)}")

    def test_application_does_not_branch_on_known_runtime_brand(self) -> None:
        forbidden_literals = (
            "pyagentskit/native@",
            "langgraph",
            "pydanticai",
            "openai agents",
            "claude agent",
            "crewai",
            "autogen",
        )

        for path in (ROOT / "application").rglob("*.py"):
            source = path.read_text(encoding="utf-8").lower()
            for literal in forbidden_literals:
                self.assertNotIn(literal, source, f"{path}: runtime brand leaked into Application")


if __name__ == "__main__":
    unittest.main()
