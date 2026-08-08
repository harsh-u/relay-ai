from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.domain.matching.pattern_repository import IntentPatternRepository
from backend.app.infrastructure.matching.postgres_patterns import (
    PostgresIntentPatternRepository,
)


async def get_intent_pattern_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> IntentPatternRepository:
    """Provide the production intent pattern repository."""
    return PostgresIntentPatternRepository(session)
