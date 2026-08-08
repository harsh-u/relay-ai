from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(slots=True, frozen=True)
class ConversationMessage:
    """A message exchanged within a RelayAI conversation."""

    conversation_id: str
    role: str
    text: str
    created_at: datetime

    @classmethod
    def assistant(
        cls,
        conversation_id: str,
        text: str,
    ) -> "ConversationMessage":
        return cls(
            conversation_id=conversation_id,
            role="assistant",
            text=text,
            created_at=datetime.now(UTC),
        )
