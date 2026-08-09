from abc import ABC, abstractmethod
from datetime import datetime

from backend.app.domain.knowledge.answered_question import AnsweredQuestion


class AnsweredQuestionRepository(ABC):
    """Business-wide cache of previously answered questions, for semantic
    reuse across different callers/conversations - not just within one call."""

    @abstractmethod
    async def save(
        self,
        tenant_id: str,
        business_id: str,
        agent_id: str,
        question: str,
        answer: str,
        embedding: list[float],
        dedup_similarity_threshold: float,
    ) -> None:
        """Cache a (question, answer) pair.

        If this same agent already has a cached question at least
        `dedup_similarity_threshold` similar to this one, that existing
        entry is refreshed in place (new answer, new embedding, new
        timestamp) instead of adding another near-duplicate row.
        """
        raise NotImplementedError

    @abstractmethod
    async def find_most_similar(
        self,
        tenant_id: str,
        business_id: str,
        agent_id: str | None,
        embedding: list[float],
        min_created_at: datetime,
    ) -> tuple[AnsweredQuestion, float] | None:
        """Return the closest cached question for this business and its
        cosine similarity to `embedding`, or None if there are no cached
        questions yet. Callers decide what similarity counts as a match.

        `agent_id`: when given, only that agent's own cached questions are
        considered (isolated scope); when None, every agent's questions for
        this business are considered (shared scope).

        `min_created_at`: cached questions older than this are ignored, so
        stale answers naturally stop being served without needing deletion.
        """
        raise NotImplementedError

    @abstractmethod
    async def clear(
        self,
        tenant_id: str,
        business_id: str,
        agent_id: str | None,
    ) -> int:
        """Delete cached questions for this business (or just one agent's,
        if given). Returns the number of rows deleted."""
        raise NotImplementedError
