from abc import ABC, abstractmethod

from backend.app.domain.knowledge.answered_question import AnsweredQuestion


class AnsweredQuestionRepository(ABC):
    """Business-wide cache of previously answered questions, for semantic
    reuse across different callers/conversations - not just within one call."""

    @abstractmethod
    async def save(
        self,
        tenant_id: str,
        business_id: str,
        question: str,
        answer: str,
        embedding: list[float],
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def find_most_similar(
        self,
        tenant_id: str,
        business_id: str,
        embedding: list[float],
    ) -> tuple[AnsweredQuestion, float] | None:
        """Return the closest cached question for this business and its
        cosine similarity to `embedding`, or None if there are no cached
        questions yet. Callers decide what similarity counts as a match."""
        raise NotImplementedError
