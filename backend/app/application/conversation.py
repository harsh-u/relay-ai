from backend.app.domain.conversation.scope import ConversationScope
from backend.app.domain.conversation.store import ConversationStore
from backend.app.domain.embedding.provider import EmbeddingProvider
from backend.app.domain.knowledge.repository import AnsweredQuestionRepository


class ConversationService:
    """Application service for conversation context updates."""

    def __init__(
        self,
        conversation_store: ConversationStore,
        embedding_provider: EmbeddingProvider,
        answered_question_repository: AnsweredQuestionRepository,
    ) -> None:
        self._conversation_store = conversation_store
        self._embedding_provider = embedding_provider
        self._answered_question_repository = answered_question_repository

    async def record_assistant_response(
        self,
        tenant_id: str,
        business_id: str,
        conversation_id: str,
        agent_id: str,
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

        last_question = await self._last_user_question(scope)

        await self._conversation_store.save_assistant_response(
            scope=scope,
            text=normalized_text,
        )

        if last_question is not None:
            await self._cache_answered_question(
                tenant_id, business_id, agent_id, last_question, normalized_text
            )

    async def _last_user_question(self, scope: ConversationScope) -> str | None:
        history = await self._conversation_store.get_recent_messages(scope=scope)

        for message in reversed(history):
            if message.role == "user":
                return message.text

        return None

    async def _cache_answered_question(
        self,
        tenant_id: str,
        business_id: str,
        agent_id: str,
        question: str,
        answer: str,
    ) -> None:
        embedding = (await self._embedding_provider.embed([question]))[0]

        await self._answered_question_repository.save(
            tenant_id=tenant_id,
            business_id=business_id,
            agent_id=agent_id,
            question=question,
            answer=answer,
            embedding=embedding,
        )
