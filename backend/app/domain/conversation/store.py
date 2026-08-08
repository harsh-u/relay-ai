from typing import Protocol

from backend.app.domain.conversation.state import ConversationState


class ConversationStore(Protocol):
    """Interface for storing short-lived conversation state."""

    async def get(self, conversation_id: str) -> ConversationState | None:
        """Return conversation state if it exists."""

    async def save(self, state: ConversationState) -> None:
        """Persist conversation state."""
