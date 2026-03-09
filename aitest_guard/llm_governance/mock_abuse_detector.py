"""Mock abuse detector: prepares context for excessive mocking detection."""

import ast
from typing import Any

from aitest_guard.models.artifact_model import Artifact


def _count_mocks_in_source(source_code: str) -> dict[str, int]:
    """Count mock/patch usage in source."""
    counts: dict[str, int] = {"patch": 0, "mock": 0, "MagicMock": 0}
    try:
        tree = ast.parse(source_code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    name = node.func.attr
                    if name in counts:
                        counts[name] += 1
                elif isinstance(node.func, ast.Name):
                    if node.func.id in counts:
                        counts[node.func.id] += 1
    except SyntaxError:
        pass
    return counts


def analyze_mock_context(artifact: Artifact, test_source: str = "") -> dict[str, Any]:
    """
    Prepare structured context for mock abuse detection. Does NOT call LLM.
    Detects excessive mocking, 100% external mocking, unrealistic mocks.
    """
    mock_counts = _count_mocks_in_source(test_source)
    total_mocks = sum(mock_counts.values())
    test_count = len(artifact.test_cases)
    context: dict[str, Any] = {
        "mock_counts": mock_counts,
        "total_mocks": total_mocks,
        "test_count": test_count,
        "mock_per_test": total_mocks / test_count if test_count else 0,
        "test_case_ids": [tc.id for tc in artifact.test_cases],
    }
    return context
