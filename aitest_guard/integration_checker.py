"""Integration test scenario enforcement for HTTP endpoints."""

from pathlib import Path
from typing import Iterator

from aitest_guard.integration_analyzer import get_endpoints


def expected_integration_test_name(handler_name: str, scenario: str) -> str:
    """Expected test name: test_<handler>_<scenario>."""
    return f"test_{handler_name}_{scenario}"


def find_integration_test_file(app_file: Path, project_root: Path) -> Path:
    """Locate integration test file for an app module."""
    rel = app_file.relative_to(project_root)
    stem = rel.stem
    candidates = [
        project_root / "tests" / "integration" / f"test_{stem}.py",
        project_root / "tests" / "integration" / f"test_{stem.replace('_', '')}.py",
        project_root / "tests" / f"test_{stem}.py",
        project_root / "test" / f"test_{stem}.py",
    ]
    for c in candidates:
        if c.exists():
            return c
    return project_root / "tests" / "integration" / f"test_{stem}.py"


def find_integration_tests_for_handler(
    test_file: Path,
    handler_name: str,
    require_docstring: bool = False,
) -> set[str]:
    """Find test_<handler>_<scenario> names in integration test file."""
    import ast

    try:
        source = test_file.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, UnicodeDecodeError, SyntaxError):
        return set()

    prefix = f"test_{handler_name}_"
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith(prefix):
            if require_docstring and not ast.get_docstring(node):
                continue
            found.add(node.name)
    return found


def check_integration_violations(
    app_files: list[Path],
    project_root: Path,
    required_scenarios: list[str],
    enforce_naming: bool,
    require_docstring: bool = False,
) -> Iterator[tuple[Path, str, str]]:
    """Yield (app_file, handler_name, missing_scenario) for each integration violation."""
    if not enforce_naming or not required_scenarios:
        return

    for app_file in app_files:
        endpoints = get_endpoints(app_file)
        for _method, _slug, handler in endpoints:
            test_file = find_integration_test_file(app_file, project_root)
            if test_file.exists():
                found = find_integration_tests_for_handler(
                    test_file, handler, require_docstring=require_docstring
                )
            else:
                found = set()

            for scenario in required_scenarios:
                expected = expected_integration_test_name(handler, scenario)
                if expected not in found:
                    yield (app_file, handler, scenario)
