"""Vague phrase validator: scan assertions and test names for forbidden phrases."""

from typing import Any

from aitest_guard.governance.base_validator import BaseValidator
from aitest_guard.models.artifact_model import Artifact
from aitest_guard.models.violation_model import Violation, ViolationCode

DEFAULT_VAGUE_PHRASES = [
    "assert result is not None",
    "assert True",
    "assert False",
    "assert response is not None",
    "assert 1",
    "assert 0",
]


class VaguePhraseValidator(BaseValidator):
    """Scan assertions and test names for forbidden vague phrases."""

    def validate(self, artifact: Artifact, policy: dict[str, Any]) -> list[Violation]:
        violations: list[Violation] = []
        gov = policy.get("ai_output_governance", {})
        vague_policy = gov.get("vague_phrase_policy", {})
        if not vague_policy.get("enabled", False):
            return violations

        phrases = vague_policy.get("forbidden_phrases", DEFAULT_VAGUE_PHRASES)
        if not phrases:
            return violations

        weight = int(vague_policy.get("violation_weight", 3))

        for tc in artifact.test_cases:
            for assertion in tc.assertions:
                for phrase in phrases:
                    if phrase in assertion:
                        violations.append(
                            Violation(
                                code=ViolationCode.VAGUE_ASSERTION,
                                message=f"Vague assertion in {tc.id}: '{phrase}'",
                                context=assertion,
                                weight=weight,
                                module=tc.module,
                                risk_tag=tc.risk_tag,
                            )
                        )
                        break
        return violations
