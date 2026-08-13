"""Architecture enforcement test: zero Django/ORM imports inside domain/.

This test uses Python's ``ast`` module to parse every .py file under
any ``domain/`` subdirectory and asserts that none of them import from
Django, the ORM, or any infrastructure-tier module.

This ensures the Clean Architecture constraint is machine-verified and
cannot be accidentally violated in future development.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

WORKSPACE_ROOT = Path(__file__).parents[3]
APPS_DIR = WORKSPACE_ROOT / "apps"

FORBIDDEN_IMPORT_PREFIXES: tuple[str, ...] = (
    "django",
    "rest_framework",
    "celery",
    "redis",
    "psycopg2",
    "infrastructure",
)


def _collect_domain_files() -> list[Path]:
    """Return all .py files that live under a domain/ directory."""
    files: list[Path] = []
    for domain_dir in APPS_DIR.rglob("domain"):
        if domain_dir.is_dir():
            files.extend(domain_dir.rglob("*.py"))
    return files


def _extract_imports(source: str) -> list[str]:
    """Parse Python source and return all imported module names."""
    tree = ast.parse(source)
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def _is_forbidden(import_name: str) -> bool:
    """Return True if the import name starts with a forbidden prefix."""
    imports_forbidden_dependency = any(
        import_name == prefix or import_name.startswith(f"{prefix}.")
        for prefix in FORBIDDEN_IMPORT_PREFIXES
    )
    imports_application_layer = ".application." in f".{import_name}."
    return imports_forbidden_dependency or imports_application_layer


@pytest.mark.parametrize("domain_file", _collect_domain_files())
def test_no_forbidden_imports_in_domain(domain_file: Path) -> None:
    """Assert that a domain file contains no forbidden infrastructure imports.

    Args:
        domain_file: Path to the domain Python file being checked.
    """
    source = domain_file.read_text(encoding="utf-8")
    all_imports = _extract_imports(source)
    violations = [imp for imp in all_imports if _is_forbidden(imp)]

    assert not violations, (
        f"Clean Architecture violation in '{domain_file.relative_to(WORKSPACE_ROOT)}'.\n"
        f"Forbidden imports found: {violations}\n"
        f"Domain layer must not import from Django, ORM, Celery, Redis, "
        f"psycopg2, or infrastructure modules."
    )
