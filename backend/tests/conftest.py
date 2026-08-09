from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.config.settings import get_settings
from backend.app.domain.analytics.repository import DecisionRepository
from backend.app.domain.business.company_repository import CompanyRepository
from backend.app.domain.business.repository import BusinessSettingsRepository
from backend.app.domain.conversation.store import ConversationStore
from backend.app.domain.embedding.provider import EmbeddingProvider
from backend.app.domain.knowledge.repository import AnsweredQuestionRepository
from backend.app.domain.matching.pattern_repository import IntentPatternRepository
from backend.app.infrastructure.analytics.dependencies import get_decision_repository
from backend.app.infrastructure.analytics.in_memory import InMemoryDecisionRepository
from backend.app.infrastructure.business.dependencies import (
    get_business_settings_repository,
    get_company_repository,
)
from backend.app.infrastructure.business.in_memory import InMemoryBusinessSettingsRepository
from backend.app.infrastructure.business.in_memory_company import InMemoryCompanyRepository
from backend.app.infrastructure.conversation.dependencies import get_conversation_store
from backend.app.infrastructure.conversation.in_memory import InMemoryConversationStore
from backend.app.infrastructure.embedding.dependencies import get_embedding_provider
from backend.app.infrastructure.embedding.fake import FakeEmbeddingProvider
from backend.app.infrastructure.knowledge.dependencies import get_answered_question_repository
from backend.app.infrastructure.knowledge.in_memory import InMemoryAnsweredQuestionRepository
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
def embedding_provider() -> FakeEmbeddingProvider:
    return FakeEmbeddingProvider()


@pytest.fixture
def answered_question_repository() -> InMemoryAnsweredQuestionRepository:
    return InMemoryAnsweredQuestionRepository()


@pytest.fixture
def business_settings_repository() -> InMemoryBusinessSettingsRepository:
    return InMemoryBusinessSettingsRepository()


@pytest.fixture
def decision_repository() -> InMemoryDecisionRepository:
    return InMemoryDecisionRepository()


@pytest.fixture
def company_repository() -> InMemoryCompanyRepository:
    return InMemoryCompanyRepository()


@pytest.fixture
def client(
    conversation_store: ConversationStore,
    pattern_repository: IntentPatternRepository,
    embedding_provider: EmbeddingProvider,
    answered_question_repository: AnsweredQuestionRepository,
    business_settings_repository: BusinessSettingsRepository,
    decision_repository: DecisionRepository,
    company_repository: CompanyRepository,
) -> Iterator[TestClient]:
    """API test client backed by isolated in-memory/fake stores.

    Unit/API tests must not depend on a developer-local PostgreSQL instance
    or the real (large) embedding model - see the *_postgres.py integration
    test files for real-DB coverage. Tests that need business-specific
    custom intent patterns, controlled embedding similarity, non-default
    knowledge-scope/TTL settings, or to inspect recorded decisions can
    additionally request the corresponding fixture to seed or inspect it.
    """

    async def _get_test_store() -> ConversationStore:
        return conversation_store

    async def _get_test_patterns() -> IntentPatternRepository:
        return pattern_repository

    async def _get_test_embeddings() -> EmbeddingProvider:
        return embedding_provider

    async def _get_test_answered_questions() -> AnsweredQuestionRepository:
        return answered_question_repository

    async def _get_test_business_settings() -> BusinessSettingsRepository:
        return business_settings_repository

    async def _get_test_decisions() -> DecisionRepository:
        return decision_repository

    async def _get_test_companies() -> CompanyRepository:
        return company_repository

    app.dependency_overrides[get_conversation_store] = _get_test_store
    app.dependency_overrides[get_intent_pattern_repository] = _get_test_patterns
    app.dependency_overrides[get_embedding_provider] = _get_test_embeddings
    app.dependency_overrides[get_answered_question_repository] = _get_test_answered_questions
    app.dependency_overrides[get_business_settings_repository] = _get_test_business_settings
    app.dependency_overrides[get_decision_repository] = _get_test_decisions
    app.dependency_overrides[get_company_repository] = _get_test_companies
    try:
        yield TestClient(app)
    finally:
        del app.dependency_overrides[get_conversation_store]
        del app.dependency_overrides[get_intent_pattern_repository]
        del app.dependency_overrides[get_embedding_provider]
        del app.dependency_overrides[get_answered_question_repository]
        del app.dependency_overrides[get_business_settings_repository]
        del app.dependency_overrides[get_decision_repository]
        del app.dependency_overrides[get_company_repository]


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
