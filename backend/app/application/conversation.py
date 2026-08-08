from backend.app.domain.conversation.scope import ConversationScope
from backend.app.domain.conversation.store import ConversationStore


class ConversationService:
    """Application service for conversation context updates."""

    def __init__(self, conversation_store: ConversationStore) -> None:
        self._conversation_store = conversation_store

    async def record_assistant_response(
        self,
        tenant_id: str,
        business_id: str,
        conversation_id: str,
        text: str,
    ) -> None:
        normalized_text = text.strip()

        if not normalized_text:
            raise ValueError("Assistant response cannot be empty.")

        scope = ConversationScope(
            tenant_id=tenant_id,
            business_id=business_id,
            conversation_id=conversation_id,
        )

        await self._conversation_store.save_assistant_response(
            scope=scope,
            text=normalized_text,
        )
