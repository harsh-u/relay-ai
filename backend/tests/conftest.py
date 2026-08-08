from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.config.settings import get_settings
from backend.app.domain.conversation.store import ConversationStore
from backend.app.infrastructure.conversation.dependencies import get_conversation_store
from backend.app.infrastructure.conversation.in_memory import InMemoryConversationStore
from backend.app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    """API test client backed by an isolated in-memory conversation store.

    Unit/API tests must not depend on a developer-local PostgreSQL instance -
    see PostgresConversationStore integration tests for real-DB coverage.
    """
    store = InMemoryConversationStore()

    async def _get_test_store() -> ConversationStore:
        return store

    app.dependency_overrides[get_conversation_store] = _get_test_store
    try:
        yield TestClient(app)
    finally:
        del app.dependency_overrides[get_conversation_store]


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
