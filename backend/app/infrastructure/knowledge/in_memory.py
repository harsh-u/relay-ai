from datetime import UTC, datetime

from backend.app.domain.embedding.similarity import cosine_similarity
from backend.app.domain.knowledge.answered_question import AnsweredQuestion
from backend.app.domain.knowledge.repository import AnsweredQuestionRepository


class InMemoryAnsweredQuestionRepository(AnsweredQuestionRepository):
    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], list[tuple[AnsweredQuestion, list[float]]]] = {}

    async def save(
        self,
        tenant_id: str,
        business_id: str,
        question: str,
        answer: str,
        embedding: list[float],
    ) -> None:
        entries = self._entries.setdefault((tenant_id, business_id), [])
        entries.append(
            (
                AnsweredQuestion(question=question, answer=answer, created_at=datetime.now(UTC)),
                embedding,
            )
        )

    async def find_most_similar(
        self,
        tenant_id: str,
        business_id: str,
        embedding: list[float],
    ) -> tuple[AnsweredQuestion, float] | None:
        entries = self._entries.get((tenant_id, business_id), [])

        best: tuple[AnsweredQuestion, float] | None = None

        for answered_question, stored_embedding in entries:
            similarity = cosine_similarity(embedding, stored_embedding)

            if best is None or similarity > best[1]:
                best = (answered_question, similarity)

        return best
