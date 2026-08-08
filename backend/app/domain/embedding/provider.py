from typing import Protocol


class EmbeddingProvider(Protocol):
    """Provider-agnostic contract for turning text into a meaning vector.

    Used to compare texts by meaning rather than by spelling/characters -
    e.g. recognizing that a rephrased question is the same question as one
    already answered earlier in a conversation.
    """

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text, in the same order."""
