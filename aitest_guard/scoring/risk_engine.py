"""Risk scoring engine: aggregate violations with context-aware multipliers."""

from typing import Any

from aitest_guard.models.violation_model import Violation, ViolationCode
from aitest_guard.scoring.severity import RiskLevel


def calculate_base_score(
    violations: list[Violation],
    policy: dict[str, Any],
) -> tuple[int, dict[str, int]]:
    """
    Compute base risk score from violations (pure function).
    Returns (base_score, breakdown).
    """
    risk_config = policy.get("risk_scoring", {})
    weights = risk_config.get("weights", {})

    breakdown: dict[str, int] = {}
    total = 0

    for v in violations:
        code = v.code.value if isinstance(v.code, ViolationCode) else str(v.code)
        w = weights.get(code, v.weight)
        total += w
        breakdown[code] = breakdown.get(code, 0) + w

    return total, breakdown


def apply_context_multipliers(
    base_score: int,
    breakdown: dict[str, int],
    violations: list[Violation],
    policy: dict[str, Any],
) -> tuple[float, dict[str, Any]]:
    """
    Apply module and classification multipliers per violation (pure function).
    Multipliers compound (module * classification per violation).
    Returns (final_score, multiplier_details).
    """
    risk_context = policy.get("risk_context", {})
    module_mults = risk_context.get("module_multipliers", {})
    class_mults = risk_context.get("classification_multipliers", {})

    if not module_mults and not class_mults:
        return float(base_score), {"base_score": base_score, "multiplier": 1.0}

    risk_config = policy.get("risk_scoring", {})
    weights = risk_config.get("weights", {})
    weighted_total = 0.0
    max_mult = 1.0

    for v in violations:
        mod_mult = 1.0
        class_mult = 1.0

        if getattr(v, "module", None) and module_mults:
            for key, val in module_mults.items():
                if key.lower() in (v.module or "").lower():
                    mod_mult = float(val)
                    break

        if getattr(v, "risk_tag", None) and class_mults:
            class_mult = float(class_mults.get(v.risk_tag or "", 1.0))

        combined = mod_mult * class_mult
        if combined > max_mult:
            max_mult = combined

        code = v.code.value if isinstance(v.code, ViolationCode) else str(v.code)
        w = weights.get(code, v.weight)
        weighted_total += w * combined

    details: dict[str, Any] = {
        "base_score": base_score,
        "multiplier": max_mult,
        "weighted_total": int(round(weighted_total)),
    }
    return weighted_total, details


def determine_risk_level(
    final_score: float,
    policy: dict[str, Any],
) -> str:
    """Determine risk level from score (pure function)."""
    risk_config = policy.get("risk_scoring", {})
    thresholds = risk_config.get("thresholds", {"low_max": 10, "medium_max": 50})
    low_max = int(thresholds.get("low_max", 10))
    medium_max = int(thresholds.get("medium_max", 50))

    if final_score <= low_max:
        return RiskLevel.LOW.value
    if final_score <= medium_max:
        return RiskLevel.MEDIUM.value
    return RiskLevel.HIGH.value


def generate_risk_breakdown(
    base_score: int,
    final_score: float,
    multiplier_details: dict[str, Any],
    breakdown: dict[str, int],
) -> dict[str, Any]:
    """Generate full risk breakdown output (pure function)."""
    mult = multiplier_details.get("multiplier", multiplier_details.get("module_multiplier", 1.0))
    return {
        "base_score": base_score,
        "final_score": int(round(final_score)),
        "multiplier_applied": mult,
        "breakdown": breakdown,
        **multiplier_details,
    }


def compute_risk_score(
    violations: list[Violation],
    policy: dict[str, Any],
) -> dict[str, Any]:
    """
    Compute risk score with context multipliers. Backward compatible.
    Returns: { base_risk_score, final_risk_score, total_score, risk_level,
               breakdown, multiplier_details }
    """
    base_score, breakdown = calculate_base_score(violations, policy)
    final_score, mult_details = apply_context_multipliers(
        base_score, breakdown, violations, policy
    )
    risk_level = determine_risk_level(final_score, policy)
    full_breakdown = generate_risk_breakdown(
        base_score, final_score, mult_details, breakdown
    )

    return {
        "base_risk_score": base_score,
        "final_risk_score": int(round(final_score)),
        "total_score": int(round(final_score)),
        "risk_level": risk_level,
        "breakdown": breakdown,
        "multiplier_details": mult_details,
    }
