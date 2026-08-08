from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.knowledge.answered_question import AnsweredQuestion
from backend.app.domain.knowledge.repository import AnsweredQuestionRepository
from backend.app.models.answered_question import AnsweredQuestionModel


class PostgresAnsweredQuestionRepository(AnsweredQuestionRepository):
    """PostgreSQL-backed answered-question cache, using pgvector for
    cosine-similarity search."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(
        self,
        tenant_id: str,
        business_id: str,
        question: str,
        answer: str,
        embedding: list[float],
    ) -> None:
        row = AnsweredQuestionModel(
            tenant_id=UUID(tenant_id),
            business_id=UUID(business_id),
            question=question,
            answer=answer,
            embedding=embedding,
        )

        self._session.add(row)
        await self._session.flush()

    async def find_most_similar(
        self,
        tenant_id: str,
        business_id: str,
        embedding: list[float],
    ) -> tuple[AnsweredQuestion, float] | None:
        distance = AnsweredQuestionModel.embedding.cosine_distance(embedding)

        statement = (
            select(AnsweredQuestionModel, distance)
            .where(
                AnsweredQuestionModel.tenant_id == UUID(tenant_id),
                AnsweredQuestionModel.business_id == UUID(business_id),
            )
            .order_by(distance)
            .limit(1)
        )

        result = await self._session.execute(statement)
        row = result.first()

        if row is None:
            return None

        model, cosine_distance = row

        return (
            AnsweredQuestion(
                question=model.question,
                answer=model.answer,
                created_at=model.created_at,
            ),
            1.0 - cosine_distance,
        )
