"""Scenario enforcement: check that required test names exist for each public function."""

from pathlib import Path
from typing import Iterator

from aitest_guard.analyzer import get_public_functions_with_risk
from aitest_guard.policy import Policy

DEFAULT_SCENARIOS = ["happy_path", "invalid_input", "exception_case"]


def _get_scenarios_for_risk(policy: Policy, risk_level: str) -> list[str]:
    """Get required scenarios for a risk level."""
    risk = policy.risk_classification
    if not risk:
        return policy.required_scenarios
    level_config = risk.get(risk_level, risk.get("standard", {}))
    return level_config.get("required_scenarios", policy.required_scenarios)


def expected_test_name(func_name: str, scenario: str) -> str:
    """Return expected pytest test function name for a function and scenario."""
    return f"test_{func_name}_{scenario}"


def find_tests_for_function(
    file_path: Path, func_name: str, require_docstring: bool = False
) -> set[str]:
    """Find test_<func>_<scenario> names defined in a test file. Optionally require docstrings."""
    import ast

    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, UnicodeDecodeError, SyntaxError):
        return set()

    prefix = f"test_{func_name}_"
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith(prefix):
            if require_docstring and not ast.get_docstring(node):
                continue
            found.add(node.name)
    return found


def find_test_file(source_file: Path, project_root: Path) -> Path:
    """Locate corresponding test file for a source file. Returns suggested path if not found."""
    rel = source_file.relative_to(project_root)
    # tests/test_foo.py for src/foo.py or foo.py
    candidates = [
        project_root / "tests" / f"test_{rel.stem}.py",
        project_root / "test" / f"test_{rel.stem}.py",
        source_file.parent / f"test_{rel.stem}.py",
        source_file.parent / "tests" / f"test_{rel.stem}.py",
    ]
    for c in candidates:
        if c.exists():
            return c
    return project_root / "tests" / f"test_{rel.stem}.py"


def check_violations(
    policy: Policy,
    source_files: list[Path],
    project_root: Path,
) -> Iterator[tuple[Path, str, str]]:
    """Yield (source_file, func_name, missing_scenario) for each violation."""
    if not policy.enforce or not policy.enforce_naming:
        return

    for source in source_files:
        funcs_with_risk = get_public_functions_with_risk(
            source, ignore_private=policy.ignore_private_functions
        )
        for func, risk_level in funcs_with_risk:
            scenarios = _get_scenarios_for_risk(policy, risk_level)
            test_file = find_test_file(source, project_root)
            if test_file and test_file.exists():
                found = find_tests_for_function(
                    test_file, func, require_docstring=policy.require_docstring
                )
            else:
                found = set()

            for scenario in scenarios:
                expected = expected_test_name(func, scenario)
                if expected not in found:
                    yield (source, func, scenario)
