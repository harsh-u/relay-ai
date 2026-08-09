from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.domain.analytics.repository import DecisionRepository
from backend.app.infrastructure.analytics.postgres import PostgresDecisionRepository


async def get_decision_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DecisionRepository:
    """Provide the production decision repository."""
    return PostgresDecisionRepository(session)
