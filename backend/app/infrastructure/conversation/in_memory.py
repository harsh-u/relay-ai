from backend.app.domain.conversation.state import ConversationState


class InMemoryConversationStore:
    """In-memory conversation store for local development and tests."""

    def __init__(self) -> None:
        self._conversations: dict[str, ConversationState] = {}

    async def get(self, conversation_id: str) -> ConversationState | None:
        return self._conversations.get(conversation_id)

    async def save(self, state: ConversationState) -> None:
        self._conversations[state.conversation_id] = state
