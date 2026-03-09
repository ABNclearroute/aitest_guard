"""Quality checks: assertions, pytest.raises, empty tests, generic assertions."""

import ast
from pathlib import Path
from typing import Iterator

from aitest_guard.analyzer import get_public_functions_with_risk
from aitest_guard.policy import Policy
from aitest_guard.scenario_checker import find_test_file


def _count_asserts_in_function(node: ast.FunctionDef) -> int:
    """Count assert statements in a function body."""
    count = 0
    for n in ast.walk(node):
        if isinstance(n, ast.Assert):
            count += 1
    return count


def _has_pytest_raises(node: ast.FunctionDef) -> bool:
    """Check if function uses pytest.raises (or with pytest.raises)."""
    for n in ast.walk(node):
        if isinstance(n, ast.With):
            for item in n.items:
                if isinstance(item.context_expr, ast.Call):
                    func = item.context_expr.func
                    if isinstance(func, ast.Attribute):
                        if func.attr == "raises":
                            if isinstance(func.value, ast.Name):
                                if func.value.id == "pytest":
                                    return True
    return False


def _is_empty_test(node: ast.FunctionDef) -> bool:
    """Check if test function body is effectively empty."""
    body = [s for s in node.body if not isinstance(s, ast.Pass)]
    return len(body) == 0


def _has_generic_assertion(node: ast.FunctionDef, disallowed: list[str]) -> bool:
    """Check if function contains any disallowed assertion pattern."""
    if not disallowed:
        return False
    try:
        source = ast.get_source_segment(ast.parse(""), "") or ""
    except Exception:
        return False
    # Use line-based check instead of AST source
    for n in ast.walk(node):
        if isinstance(n, ast.Assert):
            # Get line from parent module - we need the file content
            pass
    return False


def _get_test_function_nodes(test_file: Path, prefix: str) -> list[ast.FunctionDef]:
    """Get AST nodes for test functions matching prefix."""
    try:
        tree = ast.parse(test_file.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return []
    nodes: list[ast.FunctionDef] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith(prefix):
            nodes.append(node)
    return nodes


def _get_min_assertions(policy: Policy, source_file: Path, func_name: str) -> int:
    """Get min_assertions for a function based on its risk level."""
    min_val = policy.min_assertions_per_test
    risk = policy.risk_classification
    if not risk:
        return min_val
    for name, level in get_public_functions_with_risk(
        source_file, policy.ignore_private_functions
    ):
        if name == func_name:
            level_config = risk.get(level, risk.get("standard", {}))
            return level_config.get("min_assertions_per_test", min_val)
    return min_val


def check_quality_violations(
    policy: Policy,
    source_file: Path,
    func_name: str,
    test_file: Path,
    project_root: Path,
) -> Iterator[tuple[str, str]]:
    """Yield (test_name, violation_message) for quality violations."""
    if not test_file.exists():
        return

    prefix = f"test_{func_name}_"
    min_assertions = _get_min_assertions(policy, source_file, func_name)

    for node in _get_test_function_nodes(test_file, prefix):
        name = node.name
        if policy.disallow_empty_tests and _is_empty_test(node):
            yield (name, "empty test body")
            continue
        n_asserts = _count_asserts_in_function(node)
        if n_asserts < min_assertions:
            yield (name, f"min {min_assertions} assertion(s) required, found {n_asserts}")
        if policy.require_pytest_raises_for_exceptions and "exception" in name.lower():
            if not _has_pytest_raises(node):
                yield (name, "exception test should use pytest.raises")

    if policy.disallow_generic_assertions:
        content = test_file.read_text(encoding="utf-8")
        for pattern in policy.disallow_generic_assertions:
            if pattern in content:
                yield (func_name, f"disallowed assertion: {pattern}")
