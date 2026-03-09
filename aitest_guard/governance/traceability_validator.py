"""Traceability validator: ensure every requirement has min_test_case_per_requirement."""

from typing import Any

from aitest_guard.governance.base_validator import BaseValidator
from aitest_guard.models.artifact_model import Artifact
from aitest_guard.models.violation_model import Violation, ViolationCode


class TraceabilityValidator(BaseValidator):
    """Ensure every requirement has at least min_test_case_per_requirement test cases."""

    def validate(self, artifact: Artifact, policy: dict[str, Any]) -> list[Violation]:
        violations: list[Violation] = []
        gov = policy.get("ai_output_governance", {})
        trace = gov.get("traceability_policy", {})
        if not trace.get("enabled", False):
            return violations

        min_tests = int(trace.get("min_test_case_per_requirement", 1))
        required_ids = {r.id for r in artifact.requirements}

        for req_id in required_ids:
            linked = artifact.traceability_matrix.get(req_id, [])
            if len(linked) < min_tests:
                violations.append(
                    Violation(
                        code=ViolationCode.MISSING_TRACEABILITY,
                        message=f"Requirement {req_id} has {len(linked)} test(s), requires {min_tests}",
                        context=req_id,
                        weight=int(trace.get("violation_weight", 10)),
                    )
                )
        return violations
