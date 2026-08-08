from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.config.settings import get_settings
from backend.app.domain.conversation.store import ConversationStore
from backend.app.domain.matching.pattern_repository import IntentPatternRepository
from backend.app.infrastructure.conversation.dependencies import get_conversation_store
from backend.app.infrastructure.conversation.in_memory import InMemoryConversationStore
from backend.app.infrastructure.matching.dependencies import get_intent_pattern_repository
from backend.app.infrastructure.matching.in_memory_patterns import (
    InMemoryIntentPatternRepository,
)
from backend.app.main import app


@pytest.fixture
def conversation_store() -> ConversationStore:
    return InMemoryConversationStore()


@pytest.fixture
def pattern_repository() -> InMemoryIntentPatternRepository:
    return InMemoryIntentPatternRepository()


@pytest.fixture
def client(
    conversation_store: ConversationStore,
    pattern_repository: IntentPatternRepository,
) -> Iterator[TestClient]:
    """API test client backed by isolated in-memory stores.

    Unit/API tests must not depend on a developer-local PostgreSQL instance -
    see the *_postgres.py integration test files for real-DB coverage. Tests
    that need business-specific custom intent patterns can additionally
    request the `pattern_repository` fixture to seed it before calling.
    """

    async def _get_test_store() -> ConversationStore:
        return conversation_store

    async def _get_test_patterns() -> IntentPatternRepository:
        return pattern_repository

    app.dependency_overrides[get_conversation_store] = _get_test_store
    app.dependency_overrides[get_intent_pattern_repository] = _get_test_patterns
    try:
        yield TestClient(app)
    finally:
        del app.dependency_overrides[get_conversation_store]
        del app.dependency_overrides[get_intent_pattern_repository]


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Isolated async DB session for PostgreSQL integration tests.

    Uses its own engine with NullPool so a pooled connection is never reused
    across a different test's event loop, and rolls back on teardown so
    tests never persist state between runs.
    """
    settings = get_settings()
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_factory() as session:
        await session.begin()
        try:
            yield session
        finally:
            await session.rollback()

    await engine.dispose()
