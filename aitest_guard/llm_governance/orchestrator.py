"""Orchestrator: runs LLM governance after deterministic checks."""

from typing import Any, Protocol

from aitest_guard.llm_governance.architecture_analyzer import analyze_architecture_context
from aitest_guard.llm_governance.concurrency_analyzer import analyze_concurrency_context
from aitest_guard.llm_governance.llm_engine import run_llm_governance
from aitest_guard.llm_governance.llm_models import LLMGovernanceResult
from aitest_guard.llm_governance.mock_abuse_detector import analyze_mock_context
from aitest_guard.llm_governance.prompt_builder import build_governance_prompt
from aitest_guard.llm_governance.semantic_analyzer import analyze_semantic_context
from aitest_guard.models.artifact_model import Artifact
from aitest_guard.models.violation_model import Violation


class LLMProviderProtocol(Protocol):
    def generate(self, prompt: str) -> str:
        ...


def run_llm_governance_layer(
    artifact: Artifact,
    violations: list[Violation],
    llm_config: dict[str, Any],
    llm_provider: LLMProviderProtocol | None,
    source_code: str = "",
    test_source: str = "",
) -> dict[str, Any]:
    """
    Run optional LLM governance. Call only when llm_governance.enabled is True.
    Returns {
        llm_enabled, llm_result, llm_usage,
        base_risk_score, llm_adjustment, final_risk_score,
        llm_escalation, enforcement_action_override
    }
    Deterministic violations always take precedence. LLM may increase risk, never reduce.
    """
    enabled = llm_config.get("enabled", False)
    if not enabled or llm_provider is None:
        return {
            "llm_enabled": False,
            "llm_result": None,
            "llm_usage": None,
            "llm_adjustment": 0,
            "llm_escalation": None,
            "enforcement_action_override": None,
            "llm_mode": "advisory",
        }

    mode = llm_config.get("mode", "advisory")
    max_repo_tokens = int(llm_config.get("max_repo_tokens", 50000))
    semantic_weight = float(llm_config.get("semantic_quality_weight", 5))
    confidence_threshold = float(llm_config.get("confidence_threshold", 0.5))
    arch = llm_config.get("architecture_analysis", True)
    conc = llm_config.get("concurrency_detection", True)
    mock = llm_config.get("detect_mock_abuse", True)

    # Build analyzer context (no LLM calls)
    context: dict[str, Any] = analyze_semantic_context(artifact)
    if arch:
        context["architecture"] = analyze_architecture_context(artifact)
    if conc:
        context["concurrency"] = analyze_concurrency_context(artifact, source_code)
    if mock:
        context["mocking"] = analyze_mock_context(artifact, test_source)

    prompt = build_governance_prompt(
        artifact,
        violations,
        context,
        max_chars=max_repo_tokens * 4,
    )

    try:
        result, usage = run_llm_governance(prompt, llm_provider, max_repo_tokens)
    except Exception:
        return {
            "llm_enabled": True,
            "llm_result": None,
            "llm_usage": None,
            "llm_adjustment": 0,
            "llm_escalation": None,
            "enforcement_action_override": None,
            "llm_mode": mode,
            "llm_error": "LLM governance failed; treating as advisory only.",
        }

    llm_adjustment = 0.0
    llm_escalation: str | None = None
    enforcement_override: str | None = None

    if mode == "scoring":
        llm_adjustment = result.semantic_quality_score * semantic_weight
    elif mode == "blocking":
        if result.confidence_score < confidence_threshold:
            llm_escalation = "WARN"
            enforcement_override = "WARN"
        high_severity = any(f.severity == "high" for f in result.findings)
        if high_severity and result.confidence_score < confidence_threshold:
            llm_escalation = "FAIL"
            enforcement_override = "FAIL"

    return {
        "llm_enabled": True,
        "llm_result": result,
        "llm_usage": usage,
        "llm_adjustment": llm_adjustment,
        "llm_escalation": llm_escalation,
        "enforcement_action_override": enforcement_override,
        "llm_mode": mode,
    }
