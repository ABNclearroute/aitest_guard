"""LLM engine: invocation with token budgeting and safe fallback."""

from typing import Any, Protocol

from aitest_guard.llm_governance.llm_models import LLMGovernanceResult
from aitest_guard.llm_governance.llm_response_parser import (
    parse_llm_response,
    RETRY_INSTRUCTION,
)
from aitest_guard.llm_governance.prompt_builder import build_system_instruction


class LLMProviderProtocol(Protocol):
    """Protocol for LLM provider injection."""

    def generate(self, prompt: str) -> str:
        ...


# Approximate chars per token for English
CHARS_PER_TOKEN = 4


def _estimate_tokens(text: str) -> int:
    """Rough token estimate."""
    return len(text) // CHARS_PER_TOKEN


def run_llm_governance(
    prompt: str,
    provider: LLMProviderProtocol,
    max_repo_tokens: int = 50000,
) -> tuple[LLMGovernanceResult, dict[str, Any]]:
    """
    Invoke LLM for governance analysis.
    Returns (LLMGovernanceResult, usage_info).
    Truncates prompt to max_repo_tokens. Retries once on invalid JSON.
    """
    max_chars = max_repo_tokens * CHARS_PER_TOKEN
    if len(prompt) > max_chars:
        prompt = prompt[:max_chars] + "\n\n[... truncated for token limit ...]"

    usage: dict[str, Any] = {
        "input_tokens_estimate": _estimate_tokens(prompt),
        "output_tokens_estimate": 0,
        "retried": False,
    }

    full_prompt = build_system_instruction() + "\n\n---\n\n" + prompt
    raw = provider.generate(full_prompt)
    usage["output_tokens_estimate"] = _estimate_tokens(raw)
    result = parse_llm_response(raw)

    if not result.parse_success:
        usage["retried"] = True
        retry_prompt = full_prompt + "\n\n" + RETRY_INSTRUCTION
        raw = provider.generate(retry_prompt)
        usage["output_tokens_estimate"] += _estimate_tokens(raw)
        result = parse_llm_response(raw)

    return result, usage
