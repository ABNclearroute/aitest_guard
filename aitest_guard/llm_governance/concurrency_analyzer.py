"""Concurrency analyzer: prepares context for async and shared state detection."""

import ast
from pathlib import Path
from typing import Any

from aitest_guard.models.artifact_model import Artifact


def _source_has_async(source_code: str) -> bool:
    """Check if source contains async def."""
    try:
        tree = ast.parse(source_code)
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                return True
    except SyntaxError:
        pass
    return False


def analyze_concurrency_context(
    artifact: Artifact,
    source_code: str = "",
) -> dict[str, Any]:
    """
    Prepare structured context for concurrency analysis. Does NOT call LLM.
    Detects async functions without async tests, shared state mutation.
    """
    context: dict[str, Any] = {
        "test_case_ids": [tc.id for tc in artifact.test_cases],
        "has_async_tests": False,
        "source_has_async": _source_has_async(source_code),
    }
    for tc in artifact.test_cases:
        if tc.id.startswith("test_") and "async" in tc.id.lower():
            context["has_async_tests"] = True
            break
    return context
