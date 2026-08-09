from backend.app.domain.embedding.provider import EmbeddingProvider
from backend.app.domain.knowledge.repository import AnsweredQuestionRepository


class KnowledgeService:
    """Application service for directly managing a business's knowledge cache."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        answered_question_repository: AnsweredQuestionRepository,
        dedup_similarity_threshold: float,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._answered_question_repository = answered_question_repository
        self._dedup_similarity_threshold = dedup_similarity_threshold

    async def add_answered_question(
        self,
        tenant_id: str,
        business_id: str,
        agent_id: str,
        question: str,
        answer: str,
    ) -> None:
        """Seed the knowledge cache directly with a known (question, answer)
        pair, without waiting for a real caller to trigger a
        fallback-then-report round trip first."""

        embedding = (await self._embedding_provider.embed([question]))[0]

        await self._answered_question_repository.save(
            tenant_id=tenant_id,
            business_id=business_id,
            agent_id=agent_id,
            question=question,
            answer=answer,
            embedding=embedding,
            dedup_similarity_threshold=self._dedup_similarity_threshold,
        )
