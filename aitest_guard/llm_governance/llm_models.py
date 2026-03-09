"""Data models for LLM governance."""

from dataclasses import dataclass
from typing import Literal


@dataclass
class LLMGovernanceFinding:
    """Single advisory finding from LLM."""

    category: Literal["architecture", "concurrency", "mocking", "semantic"]
    severity: Literal["low", "medium", "high"]
    description: str
    affected_test_ids: list[str] = None

    def __post_init__(self) -> None:
        if self.affected_test_ids is None:
            self.affected_test_ids = []


@dataclass
class LLMGovernanceResult:
    """Structured response from LLM governance."""

    semantic_quality_score: int  # 0-10
    confidence_score: float  # 0-1
    findings: list[LLMGovernanceFinding]
    summary: str
    raw_response: str = ""
    parse_success: bool = True
