from datetime import UTC, datetime

from backend.app.domain.conversation.message import ConversationMessage
from backend.app.domain.conversation.scope import ConversationScope
from backend.app.domain.conversation.store import ConversationStore


class InMemoryConversationStore(ConversationStore):
    def __init__(self) -> None:
        self._messages: dict[str, list[ConversationMessage]] = {}

    async def save_assistant_response(
        self,
        scope: ConversationScope,
        text: str,
    ) -> None:
        messages = self._messages.setdefault(scope.key, [])

        messages.append(
            ConversationMessage(
                conversation_id=scope.conversation_id,
                role="assistant",
                text=text,
                created_at=datetime.now(UTC),
            )
        )

    async def get_last_assistant_response(
        self,
        scope: ConversationScope,
    ) -> ConversationMessage | None:
        messages = self._messages.get(scope.key, [])

        for message in reversed(messages):
            if message.role == "assistant":
                return message

        return None