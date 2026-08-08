from typing import Protocol

from backend.app.domain.matching.intent import Intent


class IntentMatcher(Protocol):
    """Interface for matching user text to a known intent."""

    async def match(self, text: str) -> Intent | None:
        """Return a matching intent or None."""
