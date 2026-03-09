"""Build structured prompts for LLM governance."""

import json
from typing import Any

from aitest_guard.models.artifact_model import Artifact
from aitest_guard.models.violation_model import Violation


RESPONSE_SCHEMA = """{
  "semantic_quality_score": int (0-10),
  "confidence_score": float (0-1),
  "findings": [
    {
      "category": "architecture | concurrency | mocking | semantic",
      "severity": "low | medium | high",
      "description": "string",
      "affected_test_ids": ["test_id1", "test_id2"]
    }
  ],
  "summary": "string"
}"""


def _violation_to_summary(v: Violation) -> str:
    code = v.code.value if hasattr(v.code, "value") else str(v.code)
    test_info = getattr(v, "test_id", v.context) or "N/A"
    return f"- {code}: {v.message} (context: {test_info})"


def build_governance_prompt(
    artifact: Artifact,
    violations: list[Violation],
    analyzer_context: dict[str, Any],
    max_chars: int = 15000,
) -> str:
    """
    Build prompt for LLM governance. Includes violations, artifact summary, analyzer context.
    Truncates to max_chars to respect token budget (~4 chars/token).
    """
    parts: list[str] = []

    # Deterministic violations
    if violations:
        parts.append("## Deterministic violations (from static checks)")
        parts.append("\n".join(_violation_to_summary(v) for v in violations))
        parts.append("")

    # Artifact summary (structured, not raw repo)
    artifact_summary = {
        "artifact_id": artifact.artifact_id,
        "source_module": artifact.source_module,
        "test_count": len(artifact.test_cases),
        "test_ids": [tc.id for tc in artifact.test_cases],
        "scenario_coverage": {},
        "sample_assertions": [],
    }
    for tc in artifact.test_cases:
        s = tc.scenario_type
        artifact_summary["scenario_coverage"][s] = (
            artifact_summary["scenario_coverage"].get(s, 0) + 1
        )
        for a in tc.assertions[:2]:
            artifact_summary["sample_assertions"].append({"test": tc.id, "assertion": a})
    parts.append("## Artifact summary")
    parts.append(json.dumps(artifact_summary, indent=2))
    parts.append("")

    # Analyzer context (prepared by semantic, architecture, concurrency, mock analyzers)
    parts.append("## Pre-analyzed context (for your review)")
    parts.append(json.dumps(analyzer_context, indent=2))

    full = "\n".join(parts)
    if len(full) > max_chars:
        full = full[:max_chars] + "\n\n[... truncated for token limit ...]"
    return full


def build_system_instruction() -> str:
    """System instruction for LLM governance."""
    return """You are a test quality governance assistant. Analyze ONLY the provided context.

RULES:
- Do NOT invent missing files or tests.
- If uncertain, lower confidence_score (0.5 or below).
- Only analyze what is provided. Be conservative in blocking suggestions.
- Output ONLY valid JSON matching this schema:

""" + RESPONSE_SCHEMA + """

Do not include markdown, explanations, or extra text. Return only the JSON object."""
