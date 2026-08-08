from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.domain.knowledge.repository import AnsweredQuestionRepository
from backend.app.infrastructure.knowledge.postgres import PostgresAnsweredQuestionRepository


async def get_answered_question_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AnsweredQuestionRepository:
    """Provide the production answered-question repository."""
    return PostgresAnsweredQuestionRepository(session)
