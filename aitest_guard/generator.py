"""LLM provider for governance and other optional LLM features."""

from typing import TYPE_CHECKING

from aitest_guard.policy import Policy

if TYPE_CHECKING:
    from aitest_guard.llm.base import LLMProvider


def get_llm_provider(policy: Policy) -> "LLMProvider":
    """Return configured LLM provider instance."""
    from aitest_guard.llm import OpenAIProvider

    if policy.llm_provider.lower() == "openai":
        return OpenAIProvider(
            model=policy.llm_model,
            temperature=policy.llm_temperature,
            max_tokens=policy.llm_max_tokens,
        )
    raise ValueError(f"Unknown LLM provider: {policy.llm_provider}")
