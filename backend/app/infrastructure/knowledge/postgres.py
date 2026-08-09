from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
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
        agent_id: str,
        question: str,
        answer: str,
        embedding: list[float],
        dedup_similarity_threshold: float,
    ) -> None:
        distance = AnsweredQuestionModel.embedding.cosine_distance(embedding)

        statement = (
            select(AnsweredQuestionModel, distance)
            .where(
                AnsweredQuestionModel.tenant_id == UUID(tenant_id),
                AnsweredQuestionModel.business_id == UUID(business_id),
                AnsweredQuestionModel.agent_id == agent_id,
            )
            .order_by(distance)
            .limit(1)
        )

        result = await self._session.execute(statement)
        row = result.first()

        if row is not None:
            existing, cosine_distance = row

            if 1.0 - cosine_distance >= dedup_similarity_threshold:
                existing.question = question
                existing.answer = answer
                existing.embedding = embedding
                existing.created_at = datetime.now(UTC)
                await self._session.flush()
                return

        new_row = AnsweredQuestionModel(
            tenant_id=UUID(tenant_id),
            business_id=UUID(business_id),
            agent_id=agent_id,
            question=question,
            answer=answer,
            embedding=embedding,
        )

        self._session.add(new_row)
        await self._session.flush()

    async def find_most_similar(
        self,
        tenant_id: str,
        business_id: str,
        agent_id: str | None,
        embedding: list[float],
        min_created_at: datetime,
    ) -> tuple[AnsweredQuestion, float] | None:
        distance = AnsweredQuestionModel.embedding.cosine_distance(embedding)

        conditions = [
            AnsweredQuestionModel.tenant_id == UUID(tenant_id),
            AnsweredQuestionModel.business_id == UUID(business_id),
            AnsweredQuestionModel.created_at >= min_created_at,
        ]

        if agent_id is not None:
            conditions.append(AnsweredQuestionModel.agent_id == agent_id)

        statement = (
            select(AnsweredQuestionModel, distance).where(*conditions).order_by(distance).limit(1)
        )

        result = await self._session.execute(statement)
        row = result.first()

        if row is None:
            return None

        model, cosine_distance = row

        return (
            AnsweredQuestion(
                agent_id=model.agent_id,
                question=model.question,
                answer=model.answer,
                created_at=model.created_at,
            ),
            1.0 - cosine_distance,
        )

    async def clear(
        self,
        tenant_id: str,
        business_id: str,
        agent_id: str | None,
    ) -> int:
        conditions = [
            AnsweredQuestionModel.tenant_id == UUID(tenant_id),
            AnsweredQuestionModel.business_id == UUID(business_id),
        ]

        if agent_id is not None:
            conditions.append(AnsweredQuestionModel.agent_id == agent_id)

        statement = delete(AnsweredQuestionModel).where(*conditions)
        result = await self._session.execute(statement)
        await self._session.flush()

        return result.rowcount

    async def list_all(
        self,
        tenant_id: str,
        business_id: str,
        agent_id: str | None,
    ) -> list[AnsweredQuestion]:
        conditions = [
            AnsweredQuestionModel.tenant_id == UUID(tenant_id),
            AnsweredQuestionModel.business_id == UUID(business_id),
        ]

        if agent_id is not None:
            conditions.append(AnsweredQuestionModel.agent_id == agent_id)

        statement = (
            select(AnsweredQuestionModel)
            .where(*conditions)
            .order_by(AnsweredQuestionModel.created_at.desc())
            .limit(200)
        )

        result = await self._session.execute(statement)

        return [
            AnsweredQuestion(
                agent_id=model.agent_id,
                question=model.question,
                answer=model.answer,
                created_at=model.created_at,
            )
            for model in result.scalars()
        ]
