"""Security governance validator: ensure required security scenarios for sensitive modules."""

from typing import Any

from aitest_guard.governance.base_validator import BaseValidator
from aitest_guard.models.artifact_model import Artifact
from aitest_guard.models.violation_model import Violation, ViolationCode

SENSITIVE_KEYWORDS = frozenset({"billing", "auth", "payment", "credential", "token", "secret"})


class SecurityValidator(BaseValidator):
    """Ensure modules with sensitive keywords have required security test scenarios."""

    def validate(self, artifact: Artifact, policy: dict[str, Any]) -> list[Violation]:
        violations: list[Violation] = []
        sec = policy.get("security_governance", {})
        if not sec.get("enabled", False):
            return violations

        required = set(sec.get("required_security_scenarios", []))
        if not required:
            return violations

        weight = int(sec.get("violation_weight", 15))
        risk_context = policy.get("risk_context", {})
        module_multipliers = risk_context.get("module_multipliers", {})
        sensitive_modules = frozenset(k.lower() for k in module_multipliers.keys())

        found_scenarios: set[str] = set()
        for tc in artifact.test_cases:
            if tc.scenario_type in required:
                found_scenarios.add(tc.scenario_type)

        missing = required - found_scenarios
        if not missing:
            return violations

        module_sensitive = False
        mod_lower = artifact.source_module.lower()
        for kw in SENSITIVE_KEYWORDS:
            if kw in mod_lower:
                module_sensitive = True
                break
        for sm in sensitive_modules:
            if sm in mod_lower:
                module_sensitive = True
                break

        if module_sensitive:
            violations.append(
                Violation(
                    code=ViolationCode.MISSING_SECURITY_TESTS,
                    message=f"Module '{artifact.source_module}' requires security scenarios: {sorted(missing)}",
                    context=artifact.source_module,
                    weight=weight,
                    module=artifact.source_module,
                )
            )
        return violations
