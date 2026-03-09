"""Architecture analyzer: prepares context for cross-module coverage and layered boundaries."""

from typing import Any

from aitest_guard.models.artifact_model import Artifact


def analyze_architecture_context(
    artifact: Artifact,
    source_modules: list[str] | None = None,
) -> dict[str, Any]:
    """
    Prepare structured context for architecture analysis. Does NOT call LLM.
    Detects lack of cross-module integration, missing failure propagation.
    """
    context: dict[str, Any] = {
        "source_module": artifact.source_module,
        "test_case_ids": [tc.id for tc in artifact.test_cases],
        "scenario_coverage": {},
        "single_module": True,
    }
    for tc in artifact.test_cases:
        scenario = tc.scenario_type
        context["scenario_coverage"][scenario] = context["scenario_coverage"].get(scenario, 0) + 1
    if source_modules and len(source_modules) > 1:
        context["single_module"] = False
    return context
