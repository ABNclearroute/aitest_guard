"""Weak test detection: no asserts, pass-only, generic asserts, try/except without assert."""

import ast
from pathlib import Path
from typing import Iterator

from aitest_guard.policy import Policy

DEFAULT_WEAK_PATTERNS = [
    "assert True",
    "assert False",
    "assert 1",
    "assert 0",
    "assert result is not None",
    "assert response is not None",
]

WEAK_TIP = "Add assertion validating expected output or expected exception."


def _get_assert_lines(content: str, node: ast.FunctionDef) -> list[str]:
    """Get raw lines for assert statements in a function."""
    lines = content.split("\n")
    result: list[str] = []
    for n in ast.walk(node):
        if isinstance(n, ast.Assert) and hasattr(n, "lineno"):
            line_no = n.lineno - 1
            if 0 <= line_no < len(lines):
                result.append(lines[line_no].strip())
    return result


def _count_asserts(node: ast.FunctionDef) -> int:
    """Count ast.Assert nodes in function."""
    return sum(1 for n in ast.walk(node) if isinstance(n, ast.Assert))


def _has_pytest_raises(node: ast.FunctionDef) -> bool:
    """Check if function uses pytest.raises."""
    for n in ast.walk(node):
        if isinstance(n, ast.With):
            for item in n.items:
                if isinstance(item.context_expr, ast.Call):
                    func = item.context_expr.func
                    if isinstance(func, ast.Attribute) and func.attr == "raises":
                        if isinstance(func.value, ast.Name) and func.value.id == "pytest":
                            return True
    return False


def _has_try_except(node: ast.FunctionDef) -> bool:
    """Check if function has try/except block."""
    for n in ast.walk(node):
        if isinstance(n, ast.Try):
            return True
    return False


def _is_only_pass(node: ast.FunctionDef) -> bool:
    """Test body contains only pass."""
    body = [s for s in node.body if not isinstance(s, ast.Pass)]
    return len(body) == 0 and any(isinstance(s, ast.Pass) for s in node.body)


def _is_empty_test(node: ast.FunctionDef) -> bool:
    """Empty test function (no statements or only pass)."""
    if not node.body:
        return True
    body = [s for s in node.body if not isinstance(s, ast.Pass)]
    return len(body) == 0


def _is_trivial_assert(line: str, patterns: list[str]) -> bool:
    """Check if assert line matches weak pattern."""
    for p in patterns:
        if p in line:
            return True
    return False


def _try_has_no_assert(try_node: ast.Try) -> bool:
    """Check if try body has no assert."""
    for n in ast.walk(try_node):
        if isinstance(n, ast.Assert):
            return False
    return True


def _all_asserts_are_generic(
    content: str, node: ast.FunctionDef, patterns: list[str]
) -> bool:
    """True if every assert in function matches a weak pattern."""
    lines = _get_assert_lines(content, node)
    if not lines:
        return False
    return all(_is_trivial_assert(ln, patterns) for ln in lines)


def _get_test_nodes(test_file: Path) -> list[ast.FunctionDef]:
    """Get all test function nodes."""
    try:
        tree = ast.parse(test_file.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return []
    return [
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")
    ]


def detect_weak_tests(
    test_file: Path,
    policy: Policy,
) -> Iterator[tuple[str, str, str]]:
    """Yield (test_name, reason, tip) for weak tests."""
    if not policy.weak_detection_enabled:
        return

    patterns = policy.weak_detection_patterns or DEFAULT_WEAK_PATTERNS
    try:
        content = test_file.read_text(encoding="utf-8")
    except OSError:
        return

    for node in _get_test_nodes(test_file):
        n_asserts = _count_asserts(node)
        if n_asserts == 0:
            if _is_empty_test(node):
                yield (node.name, "Empty test function.", WEAK_TIP)
            elif _is_only_pass(node):
                yield (node.name, "Test body contains only pass.", WEAK_TIP)
            elif _has_try_except(node):
                for n in ast.walk(node):
                    if isinstance(n, ast.Try) and _try_has_no_assert(n):
                        yield (
                            node.name,
                            "Test has try/except but no assert inside.",
                            WEAK_TIP,
                        )
                        break
            else:
                yield (
                    node.name,
                    "No meaningful assertion found.",
                    WEAK_TIP,
                )
            continue

        if _all_asserts_are_generic(content, node, patterns):
            yield (
                node.name,
                "Only generic assertions (e.g. assert result is not None, assert True).",
                WEAK_TIP,
            )
