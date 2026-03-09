"""Semantic analyzer: prepares context for LLM (shallow logic, trivial asserts, duplication)."""

from typing import Any

from aitest_guard.models.artifact_model import Artifact


def analyze_semantic_context(artifact: Artifact) -> dict[str, Any]:
    """
    Prepare structured context for semantic analysis. Does NOT call LLM.
    Detects shallow logic, trivial assertions, repeated patterns, duplication.
    """
    context: dict[str, Any] = {
        "test_count": len(artifact.test_cases),
        "assertion_patterns": [],
        "shallow_tests": [],
        "trivial_asserts": [],
    }
    trivial = {"assert result is not None", "assert True", "assert False", "assert 1", "assert 0"}
    assertion_texts: list[str] = []
    for tc in artifact.test_cases:
        if not tc.assertions:
            context["shallow_tests"].append(tc.id)
        for a in tc.assertions:
            assertion_texts.append(a)
            for t in trivial:
                if t in a:
                    context["trivial_asserts"].append({"test_id": tc.id, "assertion": a})
                    break
    context["assertion_count"] = len(assertion_texts)
    unique = len(set(assertion_texts))
    if len(assertion_texts) > 1 and unique < len(assertion_texts):
        context["repeated_patterns"] = True
    else:
        context["repeated_patterns"] = False
    return context
