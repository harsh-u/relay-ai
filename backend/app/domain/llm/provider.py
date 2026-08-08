from collections.abc import AsyncIterator
from typing import Protocol

from backend.app.domain.llm.message import LLMMessage


class LLMProvider(Protocol):
    """Provider-agnostic contract for calling an LLM.

    Concrete adapters (OpenAI-compatible, OpenRouter, etc.) implement this so
    application code never depends on a specific vendor SDK.
    """

    async def generate(self, messages: list[LLMMessage]) -> str:
        """Return the complete generated response text."""

    def stream(self, messages: list[LLMMessage]) -> AsyncIterator[str]:
        """Yield the generated response as it becomes available, in text chunks."""
