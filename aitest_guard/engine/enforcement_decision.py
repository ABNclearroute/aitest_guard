"""Enforcement decision: separate from validation, computes BLOCK_COMMIT | BLOCK_MERGE | WARN | ALLOW."""

from enum import Enum
from typing import Any


class EnforcementAction(str, Enum):
    """Enforcement action for compliance result."""

    BLOCK_COMMIT = "BLOCK_COMMIT"
    BLOCK_MERGE = "BLOCK_MERGE"
    WARN = "WARN"
    ALLOW = "ALLOW"


def compute_enforcement_decision(
    violations: list[Any],
    risk_level: str,
    policy: dict[str, Any],
) -> dict[str, Any]:
    """
    Compute enforcement decision. Pure function, no side effects.
    Returns: { enforcement_action, override_token?, status }
    """
    enforcement = policy.get("enforcement", {})
    block_commit = enforcement.get("block_commit", True)
    block_merge = enforcement.get("block_merge", False)
    block_release = enforcement.get("block_release", False)
    require_override = enforcement.get("require_manual_override_for_high", False)
    mode = enforcement.get("mode", "strict")

    has_violations = bool(violations)
    is_high = risk_level == "HIGH"

    override_token: str | None = None
    if require_override and is_high:
        import secrets
        override_token = secrets.token_hex(8)

    if block_merge and is_high and has_violations:
        return {
            "enforcement_action": EnforcementAction.BLOCK_MERGE.value,
            "status": "FAIL_MERGE",
            "override_token": override_token,
        }
    if block_commit and has_violations and mode == "strict":
        return {
            "enforcement_action": EnforcementAction.BLOCK_COMMIT.value,
            "status": "FAIL",
            "override_token": override_token,
        }
    if block_release and is_high:
        return {
            "enforcement_action": EnforcementAction.BLOCK_MERGE.value,
            "status": "FAIL_MERGE",
            "override_token": override_token,
        }
    if has_violations and mode == "warn":
        return {
            "enforcement_action": EnforcementAction.WARN.value,
            "status": "WARN",
            "override_token": override_token,
        }
    if has_violations:
        return {
            "enforcement_action": EnforcementAction.BLOCK_COMMIT.value,
            "status": "FAIL",
            "override_token": override_token,
        }
    return {
        "enforcement_action": EnforcementAction.ALLOW.value,
        "status": "PASS",
        "override_token": None,
    }
