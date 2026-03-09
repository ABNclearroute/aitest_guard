"""Requirement ambiguity validator: detect vague requirement descriptions."""

import re
from typing import Any

from aitest_guard.governance.base_validator import BaseValidator
from aitest_guard.models.artifact_model import Artifact
from aitest_guard.models.violation_model import Violation, ViolationCode

DEFAULT_AMBIGUITY_KEYWORDS = ["should", "may", "etc", "as needed"]
EXPLICIT_PATTERN = re.compile(r"\b(must|shall|required|will)\b", re.IGNORECASE)


class RequirementValidator(BaseValidator):
    """Flag ambiguous requirement descriptions and missing error specifications."""

    def validate(self, artifact: Artifact, policy: dict[str, Any]) -> list[Violation]:
        violations: list[Violation] = []
        req_gov = policy.get("requirement_governance", {})
        if not req_gov.get("enabled", False):
            return violations

        ambiguity_kw = req_gov.get("detect_ambiguity_keywords", DEFAULT_AMBIGUITY_KEYWORDS)
        require_explicit = req_gov.get("require_explicit_error_message", False)
        weight = int(req_gov.get("violation_weight", 8))

        for req in artifact.requirements:
            desc = (req.description or "").lower()
            for kw in ambiguity_kw:
                if kw.lower() in desc:
                    violations.append(
                        Violation(
                            code=ViolationCode.AMBIGUOUS_REQUIREMENT,
                            message=f"Requirement {req.id}: ambiguous keyword '{kw}' in description",
                            context=req.description,
                            weight=weight,
                        )
                    )
                    break

            if require_explicit and req.description:
                if not EXPLICIT_PATTERN.search(req.description):
                    violations.append(
                        Violation(
                            code=ViolationCode.MISSING_ERROR_SPECIFICATION,
                            message=f"Requirement {req.id}: missing explicit constraint (must/shall/required)",
                            context=req.description,
                            weight=weight,
                        )
                    )
        return violations
