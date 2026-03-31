"""Halo AI LLM provider — OpenAI-compatible endpoint at api.dev.halo.engineer."""

import os

from aitest_guard.llm.base import LLMProvider

HALO_BASE_URL = "https://api.dev.halo.engineer/v1/ai"


class HaloProvider(LLMProvider):
    """Halo AI API provider. Uses HALO_API_KEY env var."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.2,
        max_tokens: int = 1500,
        base_url: str = HALO_BASE_URL,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = base_url

    def generate(self, prompt: str) -> str:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError(
                "HaloProvider requires 'openai' package. "
                "Install with: pip install openai"
            ) from e

        api_key = os.environ.get("HALO_API_KEY")
        if not api_key:
            raise RuntimeError(
                "HALO_API_KEY environment variable is not set. "
                "Set it with: export HALO_API_KEY=your-key"
            )

        client = OpenAI(
            base_url=self.base_url,
            api_key=api_key,
            default_headers={"x-api-key": api_key},
        )
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        except Exception as e:
            err_str = str(e).lower()
            if "401" in err_str or "403" in err_str or "unauthorized" in err_str:
                raise RuntimeError(
                    "Halo API authentication failed. Check HALO_API_KEY."
                ) from e
            if "429" in err_str or "rate_limit" in err_str:
                raise RuntimeError("Halo API rate limit hit. Wait and retry.") from e
            raise

        return response.choices[0].message.content or ""
