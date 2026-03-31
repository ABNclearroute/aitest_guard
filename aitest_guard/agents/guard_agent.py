"""Guard Agent: validates test quality reusing existing aitest-guard AST logic."""

import ast

from aitest_guard.weak_detector import DEFAULT_WEAK_PATTERNS


def analyze_tests(code: str, tests: str) -> dict:
    """Analyze test quality against the generated code.

    Returns:
        {
            "missing_scenarios": [...],
            "weak_assertions": [...],
            "is_valid": bool,
        }
    """
    print("🔍 Validating tests...")

    func_names = _extract_function_names(code)
    test_names = _extract_test_names(tests)

    missing = _check_missing_scenarios(func_names, test_names)
    weak = _check_weak_assertions(tests)

    is_valid = len(missing) == 0 and len(weak) == 0

    status = "✅ PASS" if is_valid else "⚠️  ISSUES FOUND"
    print(f"   {status}")
    if missing:
        print(f"   Missing scenarios: {missing}")
    if weak:
        print(f"   Weak assertions: {weak}")

    return {
        "missing_scenarios": missing,
        "weak_assertions": weak,
        "is_valid": is_valid,
    }


REQUIRED_SCENARIOS = ["happy_path", "invalid_input", "exception"]


def _extract_function_names(code: str) -> list[str]:
    """Extract top-level function names from source code."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    return [
        node.name
        for node in ast.iter_child_nodes(tree)
        if isinstance(node, ast.FunctionDef)
    ]


def _extract_test_names(tests: str) -> list[str]:
    """Extract test function names from test code."""
    try:
        tree = ast.parse(tests)
    except SyntaxError:
        return []
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    ]


def _check_missing_scenarios(
    func_names: list[str], test_names: list[str]
) -> list[str]:
    """Check that each function has tests covering required scenarios."""
    missing = []
    test_names_lower = [t.lower() for t in test_names]

    for func in func_names:
        for scenario in REQUIRED_SCENARIOS:
            if not any(
                func in t and scenario in t for t in test_names_lower
            ):
                missing.append(f"{func}: {scenario}")
    return missing


def _check_weak_assertions(tests: str) -> list[str]:
    """Detect weak/trivial assertions reusing aitest-guard patterns."""
    try:
        tree = ast.parse(tests)
    except SyntaxError:
        return ["Test code has syntax errors"]

    weak = []
    lines = tests.splitlines()

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
            continue

        asserts = [n for n in ast.walk(node) if isinstance(n, ast.Assert)]
        has_pytest_raises = _has_pytest_raises(node)

        if len(asserts) == 0 and not has_pytest_raises:
            weak.append(f"{node.name}: no assertions")
            continue

        for a in asserts:
            line_idx = a.lineno - 1
            if 0 <= line_idx < len(lines):
                line = lines[line_idx].strip()
                for pattern in DEFAULT_WEAK_PATTERNS:
                    if pattern in line:
                        weak.append(f"{node.name}: trivial assertion '{pattern}'")
                        break

    return weak


def _has_pytest_raises(node: ast.FunctionDef) -> bool:
    """Check if function uses pytest.raises (reused from weak_detector logic)."""
    for n in ast.walk(node):
        if isinstance(n, ast.With):
            for item in n.items:
                if isinstance(item.context_expr, ast.Call):
                    func = item.context_expr.func
                    if (
                        isinstance(func, ast.Attribute)
                        and func.attr == "raises"
                        and isinstance(func.value, ast.Name)
                        and func.value.id == "pytest"
                    ):
                        return True
    return False
