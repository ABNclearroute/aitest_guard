"""Parse LLM governance responses with retry and safe fallback."""

import json
import re
from typing import Any

from aitest_guard.llm_governance.llm_models import (
    LLMGovernanceResult,
    LLMGovernanceFinding,
)


def _parse_finding(obj: dict[str, Any]) -> LLMGovernanceFinding:
    category = obj.get("category", "semantic")
    if category not in ("architecture", "concurrency", "mocking", "semantic"):
        category = "semantic"
    severity = obj.get("severity", "low")
    if severity not in ("low", "medium", "high"):
        severity = "low"
    return LLMGovernanceFinding(
        category=category,
        severity=severity,
        description=str(obj.get("description", "")),
        affected_test_ids=list(obj.get("affected_test_ids", [])),
    )


def parse_llm_response(raw: str) -> LLMGovernanceResult:
    """
    Parse LLM JSON response. Returns LLMGovernanceResult.
    On invalid JSON, returns fallback with parse_success=False.
    """
    raw = raw.strip()
    # Try to extract JSON block
    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        raw = match.group(0)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return LLMGovernanceResult(
            semantic_quality_score=5,
            confidence_score=0.0,
            findings=[],
            summary="LLM response could not be parsed. Treating as advisory only.",
            raw_response=raw[:500],
            parse_success=False,
        )
    findings: list[LLMGovernanceFinding] = []
    for f in data.get("findings", []):
        if isinstance(f, dict):
            try:
                findings.append(_parse_finding(f))
            except (KeyError, TypeError):
                pass
    return LLMGovernanceResult(
        semantic_quality_score=int(data.get("semantic_quality_score", 5)),
        confidence_score=float(data.get("confidence_score", 0.5)),
        findings=findings,
        summary=str(data.get("summary", "")),
        raw_response=raw[:500],
        parse_success=True,
    )


RETRY_INSTRUCTION = (
    "Output ONLY a valid JSON object. No markdown, no code blocks, no extra text. "
    "Copy the schema exactly and fill in the values."
)
