"""OpenAI LLM provider implementation."""

import os

from aitest_guard.llm.base import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI API provider. Uses OPENAI_API_KEY env var."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.2,
        max_tokens: int = 1200,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def generate(self, prompt: str) -> str:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError(
                "OpenAI provider requires 'openai' package. "
                "Install with: pip install aitest-guard[openai]"
            ) from e

        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError(
                "OPENAI_API_KEY environment variable is not set. "
                "Set it with: export OPENAI_API_KEY=sk-your-key"
            )

        client = OpenAI()
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "quota" in err_str or "insufficient_quota" in err_str:
                raise RuntimeError(
                    "OpenAI API quota exceeded. Check your billing at "
                    "https://platform.openai.com/account/billing"
                ) from e
            if "401" in err_str or "invalid_api_key" in err_str:
                raise RuntimeError("Invalid OpenAI API key. Check OPENAI_API_KEY.") from e
            if "rate_limit" in err_str:
                raise RuntimeError(
                    "OpenAI rate limit hit. Wait a moment and try again."
                ) from e
            raise

        return response.choices[0].message.content or ""
