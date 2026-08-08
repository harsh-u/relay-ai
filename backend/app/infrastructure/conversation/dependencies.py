from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.domain.conversation.store import ConversationStore
from backend.app.infrastructure.conversation.postgres import (
    PostgresConversationStore,
)


async def get_conversation_store(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ConversationStore:
    """Provide the production conversation store."""
    return PostgresConversationStore(session)
