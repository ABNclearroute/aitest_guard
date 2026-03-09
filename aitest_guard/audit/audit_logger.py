"""Audit logger: JSONL logs under logs/audit/ with retention and configurable fields."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from aitest_guard.models.artifact_model import Artifact
from aitest_guard.models.violation_model import Violation


def _get_audit_config(policy: dict[str, Any]) -> dict[str, Any]:
    """Get audit config from policy with defaults."""
    audit = policy.get("audit", {})
    return {
        "enabled": audit.get("enabled", True),
        "retention_days": int(audit.get("retention_days", 90)),
        "include_artifact_snapshot": audit.get("include_artifact_snapshot", False),
        "include_risk_score": audit.get("include_risk_score", True),
    }


def _ensure_log_dir() -> Path:
    """Ensure logs/audit directory exists."""
    root = Path.cwd()
    audit_dir = root / "logs" / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    return audit_dir


def _violations_to_dict(violations: list[Violation]) -> list[dict[str, Any]]:
    """Convert Violation list to JSON-serializable dicts."""
    return [
        {
            "code": v.code.value if hasattr(v.code, "value") else str(v.code),
            "message": v.message,
            "context": v.context,
            "weight": v.weight,
        }
        for v in violations
    ]


def _artifact_to_dict(artifact: Artifact | None) -> dict[str, Any] | None:
    """Serialize artifact for snapshot."""
    if not artifact:
        return None
    return {
        "artifact_id": artifact.artifact_id,
        "source_module": artifact.source_module,
        "contract_version": getattr(artifact, "contract_version", None),
        "test_case_count": len(artifact.test_cases),
        "requirement_count": len(artifact.requirements),
    }


def _prune_old_logs(log_dir: Path, retention_days: int) -> None:
    """Remove log entries older than retention_days."""
    if retention_days <= 0:
        return
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    log_file = log_dir / "audit.jsonl"
    if not log_file.exists():
        return
    kept: list[str] = []
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                ts = entry.get("timestamp", "")
                if ts:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if dt >= cutoff:
                        kept.append(line)
            except (json.JSONDecodeError, ValueError):
                kept.append(line)
    with open(log_file, "w", encoding="utf-8") as f:
        for line in kept:
            f.write(line + "\n")


def _llm_governance_to_dict(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Serialize LLM governance data for audit. Never include API keys or full prompt by default."""
    if not data:
        return None
    out: dict[str, Any] = {
        "semantic_quality_score": data.get("semantic_quality_score"),
        "llm_confidence": data.get("llm_confidence"),
        "llm_mode": data.get("llm_mode"),
        "llm_findings": data.get("llm_findings", []),
    }
    if not any(out.values()):
        return None
    return out


def log_audit_entry(
    event: str,
    policy_name: str,
    artifact_id: str,
    violations: list[Violation],
    risk_score: int,
    risk_level: str,
    policy: dict[str, Any] | None = None,
    artifact: Artifact | None = None,
    risk_breakdown: dict[str, Any] | None = None,
    llm_governance_data: dict[str, Any] | None = None,
) -> None:
    """Write a single audit log entry with configurable fields."""
    if policy:
        config = _get_audit_config(policy)
        if not config.get("enabled", True):
            return
        retention = config.get("retention_days", 90)
        include_snapshot = config.get("include_artifact_snapshot", False)
        include_risk = config.get("include_risk_score", True)
    else:
        retention = 90
        include_snapshot = False
        include_risk = True

    log_dir = _ensure_log_dir()
    log_file = log_dir / "audit.jsonl"

    entry: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "policy_name": policy_name,
        "policy_version": str(policy.get("output_contract", {}).get("version", "1.0")) if policy else "1.0",
        "artifact_id": artifact_id,
        "violations": _violations_to_dict(violations),
    }

    if include_risk:
        entry["risk_score"] = risk_score
        entry["risk_level"] = risk_level
        if risk_breakdown:
            entry["risk_breakdown"] = risk_breakdown

    if include_snapshot and artifact:
        entry["snapshot"] = _artifact_to_dict(artifact)

    llm_data = _llm_governance_to_dict(llm_governance_data)
    if llm_data:
        entry["llm_governance"] = llm_data
    if llm_governance_data and include_snapshot and llm_governance_data.get("llm_prompt_snapshot"):
        entry["llm_prompt_snapshot"] = llm_governance_data["llm_prompt_snapshot"]

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    _prune_old_logs(log_dir, retention)


def log_violations(
    policy_name: str,
    artifact_id: str,
    violations: list[Violation],
    risk_score: int,
    risk_level: str,
    policy: dict[str, Any] | None = None,
    artifact: Artifact | None = None,
    risk_breakdown: dict[str, Any] | None = None,
    llm_governance_data: dict[str, Any] | None = None,
) -> None:
    """Log violations found event."""
    log_audit_entry(
        "violations_found", policy_name, artifact_id,
        violations, risk_score, risk_level,
        policy, artifact, risk_breakdown, llm_governance_data,
    )


def log_artifact_rejected(
    policy_name: str,
    artifact_id: str,
    violations: list[Violation],
    risk_score: int,
    risk_level: str,
    policy: dict[str, Any] | None = None,
    artifact: Artifact | None = None,
    risk_breakdown: dict[str, Any] | None = None,
    llm_governance_data: dict[str, Any] | None = None,
) -> None:
    """Log artifact rejected event."""
    log_audit_entry(
        "artifact_rejected", policy_name, artifact_id,
        violations, risk_score, risk_level,
        policy, artifact, risk_breakdown, llm_governance_data,
    )


def log_high_risk(
    policy_name: str,
    artifact_id: str,
    violations: list[Violation],
    risk_score: int,
    risk_level: str,
    policy: dict[str, Any] | None = None,
    artifact: Artifact | None = None,
    risk_breakdown: dict[str, Any] | None = None,
    llm_governance_data: dict[str, Any] | None = None,
) -> None:
    """Log high risk level event."""
    log_audit_entry(
        "high_risk", policy_name, artifact_id,
        violations, risk_score, risk_level,
        policy, artifact, risk_breakdown, llm_governance_data,
    )


class AuditLogger:
    """Convenience wrapper for audit logging."""

    def __init__(self, policy_name: str = "default", policy: dict[str, Any] | None = None) -> None:
        self.policy_name = policy_name
        self.policy = policy

    def violations(
        self,
        artifact_id: str,
        violations: list[Violation],
        risk_score: int,
        risk_level: str,
        artifact: Artifact | None = None,
        risk_breakdown: dict[str, Any] | None = None,
        llm_governance_data: dict[str, Any] | None = None,
    ) -> None:
        log_violations(
            self.policy_name, artifact_id, violations, risk_score, risk_level,
            self.policy, artifact, risk_breakdown, llm_governance_data,
        )

    def rejected(
        self,
        artifact_id: str,
        violations: list[Violation],
        risk_score: int,
        risk_level: str,
        artifact: Artifact | None = None,
        risk_breakdown: dict[str, Any] | None = None,
        llm_governance_data: dict[str, Any] | None = None,
    ) -> None:
        log_artifact_rejected(
            self.policy_name, artifact_id, violations, risk_score, risk_level,
            self.policy, artifact, risk_breakdown, llm_governance_data,
        )

    def high_risk(
        self,
        artifact_id: str,
        violations: list[Violation],
        risk_score: int,
        risk_level: str,
        artifact: Artifact | None = None,
        risk_breakdown: dict[str, Any] | None = None,
        llm_governance_data: dict[str, Any] | None = None,
    ) -> None:
        log_high_risk(
            self.policy_name, artifact_id, violations, risk_score, risk_level,
            self.policy, artifact, risk_breakdown, llm_governance_data,
        )


audit_logger = AuditLogger()
