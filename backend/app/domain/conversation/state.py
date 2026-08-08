from dataclasses import dataclass


@dataclass(slots=True)
class ConversationState:
    """Minimal state RelayAI needs for a conversation."""

    conversation_id: str
    last_user_message: str | None = None
    last_assistant_response: str | None = None
