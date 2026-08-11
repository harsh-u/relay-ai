from datetime import UTC, datetime

from backend.app.domain.conversation.message import ConversationMessage
from backend.app.domain.conversation.scope import ConversationScope
from backend.app.domain.conversation.store import ConversationStore
from backend.app.domain.conversation.summary import ConversationSummary


class InMemoryConversationStore(ConversationStore):
    def __init__(self) -> None:
        self._messages: dict[str, list[ConversationMessage]] = {}

    async def save_user_message(
        self,
        scope: ConversationScope,
        text: str,
    ) -> None:
        messages = self._messages.setdefault(scope.key, [])

        messages.append(
            ConversationMessage(
                conversation_id=scope.conversation_id,
                role="user",
                text=text,
                created_at=datetime.now(UTC),
            )
        )

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

    async def get_recent_messages(
        self,
        scope: ConversationScope,
        limit: int = 20,
    ) -> list[ConversationMessage]:
        messages = self._messages.get(scope.key, [])
        return messages[-limit:]

    async def list_recent_conversations(
        self,
        tenant_id: str,
        business_id: str,
        limit: int = 20,
    ) -> list[ConversationSummary]:
        prefix = f"{tenant_id}:{business_id}:"
        summaries = []

        for key, messages in self._messages.items():
            if not key.startswith(prefix) or not messages:
                continue

            last = messages[-1]
            summaries.append(
                ConversationSummary(
                    conversation_id=key.removeprefix(prefix),
                    last_message_role=last.role,
                    last_message_text=last.text,
                    last_message_at=last.created_at,
                )
            )

        summaries.sort(key=lambda summary: summary.last_message_at, reverse=True)
        return summaries[:limit]

    async def purge_expired(self, older_than: datetime) -> int:
        deleted = 0

        for key, messages in self._messages.items():
            remaining = [message for message in messages if message.created_at >= older_than]
            deleted += len(messages) - len(remaining)
            self._messages[key] = remaining

        return deleted
