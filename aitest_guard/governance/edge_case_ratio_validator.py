"""Edge case ratio validator: ensure minimum ratio of edge/invalid_input tests."""

from typing import Any

from aitest_guard.governance.base_validator import BaseValidator
from aitest_guard.models.artifact_model import Artifact
from aitest_guard.models.violation_model import Violation, ViolationCode


class EdgeCaseRatioValidator(BaseValidator):
    """Validate ratio of edge_case + invalid_input tests meets policy minimum."""

    def validate(self, artifact: Artifact, policy: dict[str, Any]) -> list[Violation]:
        violations: list[Violation] = []
        gov = policy.get("ai_output_governance", {})
        edge_policy = gov.get("edge_case_policy", {})
        if not edge_policy.get("enabled", False):
            return violations

        min_ratio = float(edge_policy.get("min_ratio", 0.2))
        test_cases = artifact.test_cases
        if not test_cases:
            return violations

        edge_types = {"edge_case", "invalid_input"}
        edge_count = sum(1 for tc in test_cases if tc.scenario_type in edge_types)
        actual_ratio = edge_count / len(test_cases)

        if actual_ratio < min_ratio:
            violations.append(
                Violation(
                    code=ViolationCode.LOW_EDGE_COVERAGE,
                    message=f"Edge/invalid_input ratio {actual_ratio:.2f} below minimum {min_ratio}",
                    context=f"{edge_count}/{len(test_cases)} tests",
                    weight=int(edge_policy.get("violation_weight", 5)),
                )
            )
        return violations
