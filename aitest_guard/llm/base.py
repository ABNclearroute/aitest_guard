"""Base LLM provider interface."""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base for LLM providers. Implement generate() for each provider."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate text from prompt. Returns raw model output."""
        raise NotImplementedError
