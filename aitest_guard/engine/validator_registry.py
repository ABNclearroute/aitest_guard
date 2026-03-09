"""Dynamic validator registry: load validators from policy.yaml."""

from typing import Any, Protocol

from aitest_guard.audit.audit_logger import AuditLogger
from aitest_guard.engine.enforcement_decision import compute_enforcement_decision
from aitest_guard.governance.deterministic_format_validator import DeterministicFormatValidator
from aitest_guard.governance.edge_case_ratio_validator import EdgeCaseRatioValidator
from aitest_guard.governance.requirement_validator import RequirementValidator
from aitest_guard.governance.security_validator import SecurityValidator
from aitest_guard.governance.traceability_validator import TraceabilityValidator
from aitest_guard.governance.vague_phrase_validator import VaguePhraseValidator
from aitest_guard.models.artifact_model import Artifact
from aitest_guard.models.violation_model import Violation
from aitest_guard.scoring.risk_engine import compute_risk_score, determine_risk_level
from aitest_guard.scoring.severity import RiskLevel


class ValidatorRegistry:
    """Dynamically register validators based on policy sections."""

    _VALIDATOR_MAP = {
        "traceability": (TraceabilityValidator, "traceability_policy", "ai_output_governance"),
        "edge_case_ratio": (EdgeCaseRatioValidator, "edge_case_policy", "ai_output_governance"),
        "vague_phrase": (VaguePhraseValidator, "vague_phrase_policy", "ai_output_governance"),
        "deterministic_format": (DeterministicFormatValidator, "deterministic_format_policy", "ai_output_governance"),
        "security": (SecurityValidator, "security_governance", None),
        "requirement": (RequirementValidator, "requirement_governance", None),
    }

    def __init__(self) -> None:
        self._validators: list[tuple[Any, str]] = []

    def load_from_policy(self, policy: dict[str, Any]) -> "ValidatorRegistry":
        """Load validators based on enabled policy sections."""
        self._validators.clear()
        for key, (cls, section, parent) in self._VALIDATOR_MAP.items():
            if parent:
                config = policy.get(parent, {}).get(section, {})
            else:
                config = policy.get(section, {})
            if config.get("enabled", False):
                self._validators.append((cls(), section))
        return self

    def validate(self, artifact: Artifact, policy: dict[str, Any]) -> list[Violation]:
        """Run all registered validators and return combined violations."""
        all_violations: list[Violation] = []
        for validator, _ in self._validators:
            all_violations.extend(validator.validate(artifact, policy))
        return all_violations


class LLMProviderProtocol(Protocol):
    def generate(self, prompt: str) -> str:
        ...


def run_governance(
    artifact: Artifact,
    policy: dict[str, Any],
    policy_name: str = "default",
    enforcement_mode: str | None = None,
    llm_provider: LLMProviderProtocol | None = None,
    test_source: str = "",
    source_code: str = "",
) -> dict[str, Any]:
    """
    Run governance validation and return compliance result contract.
    Deterministic validation always runs first. LLM governance runs after if enabled.
    Deterministic violations always take precedence; LLM may increase risk, never reduce.
    {
        status, enforcement_action, base_risk_score, final_risk_score,
        risk_level, multiplier_details, violations, recommendations,
        llm_findings, llm_confidence, llm_adjustment (optional)
    }
    """
    registry = ValidatorRegistry()
    registry.load_from_policy(policy)

    violations = registry.validate(artifact, policy)
    score_result = compute_risk_score(violations, policy)

    base_score = score_result.get("base_risk_score", score_result.get("total_score", 0))
    final_score = score_result.get("final_risk_score", score_result.get("total_score", 0))
    risk_level = score_result["risk_level"]
    multiplier_details = score_result.get("multiplier_details", {})
    breakdown = score_result.get("breakdown", {})

    enforcement = policy.get("enforcement", {})
    mode = enforcement_mode or enforcement.get("mode", "strict")
    enforcement["mode"] = mode

    decision = compute_enforcement_decision(violations, risk_level, policy)
    enforcement_action = decision["enforcement_action"]
    status = decision["status"]

    llm_governance_data: dict[str, Any] | None = None
    llm_config = policy.get("llm_governance", {})
    if llm_config.get("enabled", False) and llm_provider is not None:
        from aitest_guard.llm_governance.orchestrator import run_llm_governance_layer

        llm_out = run_llm_governance_layer(
            artifact=artifact,
            violations=violations,
            llm_config=llm_config,
            llm_provider=llm_provider,
            source_code=source_code,
            test_source=test_source,
        )
        if llm_out.get("llm_enabled") and llm_out.get("llm_result"):
            res = llm_out["llm_result"]
            llm_adjustment = llm_out.get("llm_adjustment", 0)
            llm_mode = llm_out.get("llm_mode", "advisory")

            if llm_mode == "scoring":
                final_score = base_score + llm_adjustment
                risk_level = determine_risk_level(final_score, policy)
                breakdown["llm_adjustment"] = llm_adjustment

            if llm_mode == "blocking":
                override = llm_out.get("enforcement_action_override")
                if override and status not in ("FAIL", "FAIL_MERGE"):
                    status = "FAIL" if override == "FAIL" else "WARN"
                    enforcement_action = "BLOCK_COMMIT" if override == "FAIL" else "WARN"

            llm_governance_data = {
                "semantic_quality_score": res.semantic_quality_score,
                "llm_confidence": res.confidence_score,
                "llm_mode": llm_mode,
                "llm_findings": [
                    {
                        "category": f.category,
                        "severity": f.severity,
                        "description": f.description,
                        "affected_test_ids": f.affected_test_ids,
                    }
                    for f in res.findings
                ],
            }
            audit_config = policy.get("audit", {})
            if audit_config.get("include_artifact_snapshot", False):
                llm_governance_data["llm_prompt_snapshot"] = True

    audit = AuditLogger(policy_name=policy_name, policy=policy)
    risk_breakdown = {"base": base_score, "final": final_score, "breakdown": breakdown}

    if violations:
        audit.violations(
            artifact.artifact_id, violations, final_score, risk_level,
            artifact=artifact, risk_breakdown=risk_breakdown,
            llm_governance_data=llm_governance_data,
        )
    if risk_level == RiskLevel.HIGH.value:
        audit.high_risk(
            artifact.artifact_id, violations, final_score, risk_level,
            artifact=artifact, risk_breakdown=risk_breakdown,
            llm_governance_data=llm_governance_data,
        )
    if decision.get("status") in ("FAIL", "FAIL_MERGE"):
        audit.rejected(
            artifact.artifact_id, violations, final_score, risk_level,
            artifact=artifact, risk_breakdown=risk_breakdown,
            llm_governance_data=llm_governance_data,
        )

    recommendations = _build_recommendations(violations)

    result: dict[str, Any] = {
        "status": status,
        "enforcement_action": enforcement_action,
        "base_risk_score": base_score,
        "final_risk_score": final_score,
        "risk_score": final_score,  # backward compat
        "risk_level": risk_level,
        "multiplier_details": multiplier_details,
        "violations": violations,
        "recommendations": recommendations,
        "breakdown": breakdown,
    }
    if decision.get("override_token"):
        result["override_token"] = decision["override_token"]
    if llm_governance_data:
        result["llm_findings"] = llm_governance_data.get("llm_findings", [])
        result["llm_confidence"] = llm_governance_data.get("llm_confidence")
        result["llm_mode"] = llm_governance_data.get("llm_mode")
    return result


def _build_recommendations(violations: list[Violation]) -> list[str]:
    """Build human-readable recommendations from violations."""
    recs: list[str] = []
    codes_seen: set[str] = set()
    for v in violations:
        code = v.code.value if hasattr(v.code, "value") else str(v.code)
        if code not in codes_seen:
            codes_seen.add(code)
            if "TRACEABILITY" in code:
                recs.append("Add more test cases to cover each requirement.")
            elif "EDGE_COVERAGE" in code:
                recs.append("Increase edge_case and invalid_input test coverage.")
            elif "VAGUE" in code or "GENERIC" in code:
                recs.append("Replace generic assertions with meaningful assertions.")
            elif "FORMAT" in code:
                recs.append("Ensure test names follow test_<func>_<scenario> and have assertions.")
            elif "SECURITY" in code:
                recs.append("Add required security scenarios for sensitive modules.")
            elif "AMBIGUOUS" in code or "ERROR_SPECIFICATION" in code:
                recs.append("Use explicit requirement language (must, shall, required).")
            elif "CONTRACT_VERSION" in code:
                recs.append("Align artifact contract version with policy output_contract.version.")
    return recs
