"""Deterministic format validator: ensure required_test_fields and contract version."""

from typing import Any

from aitest_guard.governance.base_validator import BaseValidator
from aitest_guard.models.artifact_model import Artifact
from aitest_guard.models.test_case_model import TestCase
from aitest_guard.models.violation_model import Violation, ViolationCode


class DeterministicFormatValidator(BaseValidator):
    """Ensure each test case has required fields and contract version matches."""

    def validate(self, artifact: Artifact, policy: dict[str, Any]) -> list[Violation]:
        violations: list[Violation] = []
        gov = policy.get("ai_output_governance", {})
        format_policy = gov.get("deterministic_format_policy", {})
        output_contract = policy.get("output_contract", {})

        if output_contract.get("enforce_version_match", False):
            expected = str(output_contract.get("version", "1.0"))
            actual = getattr(artifact, "contract_version", None) or ""
            if actual and actual != expected:
                violations.append(
                    Violation(
                        code=ViolationCode.CONTRACT_VERSION_MISMATCH,
                        message=f"Contract version mismatch: expected {expected}, got {actual}",
                        context=artifact.artifact_id,
                        weight=int(format_policy.get("violation_weight", 5)),
                    )
                )

        if not format_policy.get("enabled", False):
            return violations

        required_fields = format_policy.get("required_test_fields", ["id", "scenario_type"])
        weight = int(format_policy.get("violation_weight", 5))

        for tc in artifact.test_cases:
            for field in required_fields:
                if field == "id" and (not tc.id or not tc.id.startswith("test_")):
                    violations.append(
                        Violation(
                            code=ViolationCode.FORMAT_VIOLATION,
                            message=f"Test case missing valid id (must start with test_): {tc.id!r}",
                            context=tc.id or "unnamed",
                            weight=weight,
                            module=tc.module,
                            risk_tag=tc.risk_tag,
                        )
                    )
                elif field == "scenario_type" and tc.scenario_type == "unknown":
                    violations.append(
                        Violation(
                            code=ViolationCode.FORMAT_VIOLATION,
                            message=f"Test case {tc.id} has unknown scenario_type",
                            context=tc.id,
                            weight=weight,
                            module=tc.module,
                            risk_tag=tc.risk_tag,
                        )
                    )
                elif field == "assertions" and not tc.assertions:
                    violations.append(
                        Violation(
                            code=ViolationCode.FORMAT_VIOLATION,
                            message=f"Test case {tc.id} has no assertions",
                            context=tc.id,
                            weight=weight,
                            module=tc.module,
                            risk_tag=tc.risk_tag,
                        )
                    )
        return violations
