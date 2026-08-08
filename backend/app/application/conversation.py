from backend.app.domain.conversation.store import ConversationStore


class ConversationService:
    """Application service for conversation context updates."""

    def __init__(self, conversation_store: ConversationStore) -> None:
        self._conversation_store = conversation_store

    async def record_assistant_response(
        self,
        conversation_id: str,
        text: str,
    ) -> None:
        normalized_text = text.strip()

        if not normalized_text:
            raise ValueError("Assistant response cannot be empty.")

        await self._conversation_store.save_assistant_response(
            conversation_id=conversation_id,
            text=normalized_text,
        )
