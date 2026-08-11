from abc import ABC, abstractmethod
from datetime import datetime

from backend.app.domain.conversation.message import ConversationMessage
from backend.app.domain.conversation.scope import ConversationScope


class ConversationStore(ABC):
    @abstractmethod
    async def save_user_message(
        self,
        scope: ConversationScope,
        text: str,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save_assistant_response(
        self,
        scope: ConversationScope,
        text: str,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_last_assistant_response(
        self,
        scope: ConversationScope,
    ) -> ConversationMessage | None:
        raise NotImplementedError

    @abstractmethod
    async def get_recent_messages(
        self,
        scope: ConversationScope,
        limit: int = 20,
    ) -> list[ConversationMessage]:
        """Return up to `limit` most recent messages, oldest first."""
        raise NotImplementedError

    @abstractmethod
    async def purge_expired(self, older_than: datetime) -> int:
        """Delete every stored message older than `older_than`, across every
        tenant/business/conversation. Returns the number of rows deleted.

        Every read on this store is scoped to a single active conversation
        and looks back at most a handful of messages - nothing needs a
        message once its conversation has gone cold. Meant to be run
        periodically (see scripts/purge_expired_conversation_messages.py),
        not on any request path.
        """
        raise NotImplementedError
