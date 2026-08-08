from abc import ABC, abstractmethod

from backend.app.domain.conversation.message import ConversationMessage
from backend.app.domain.conversation.scope import ConversationScope


class ConversationStore(ABC):
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
