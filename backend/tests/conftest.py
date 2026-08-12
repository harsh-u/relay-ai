from collections.abc import AsyncIterator, Iterator
from typing import Annotated

import pytest
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.config.settings import get_settings
from backend.app.domain.analytics.repository import DecisionRepository
from backend.app.domain.auth.repository import ApiKeyRepository
from backend.app.domain.business.company_repository import CompanyRepository
from backend.app.domain.business.repository import BusinessSettingsRepository
from backend.app.domain.conversation.store import ConversationStore
from backend.app.domain.embedding.provider import EmbeddingProvider
from backend.app.domain.knowledge.repository import AnsweredQuestionRepository
from backend.app.domain.matching.pattern_repository import IntentPatternRepository
from backend.app.domain.users.user import User
from backend.app.infrastructure.analytics.dependencies import get_decision_repository
from backend.app.infrastructure.analytics.in_memory import InMemoryDecisionRepository
from backend.app.infrastructure.auth.dependencies import (
    get_api_key_repository,
    get_authenticated_tenant_id,
)
from backend.app.infrastructure.auth.in_memory import InMemoryApiKeyRepository
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
from backend.app.infrastructure.users.dependencies import (
    get_current_user_or_none,
    get_user_repository,
)
from backend.app.infrastructure.users.in_memory import InMemoryUserRepository
from backend.app.main import app

_test_bearer_scheme = HTTPBearer(auto_error=False)


async def _fake_authenticated_tenant_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(_test_bearer_scheme)],
) -> str:
    """Test-only stand-in for get_authenticated_tenant_id: parses
    'Bearer test:<tenant_id>' and returns <tenant_id> directly, with no
    real hashing/lookup - so a test can use any tenant_id string without
    first registering a real key for it. Used by the `client` fixture;
    `client_with_real_auth` leaves the real dependency in place instead."""
    if credentials is None or not credentials.credentials.startswith("test:"):
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header. Expected 'Bearer test:<tenant_id>'.",
        )

    return credentials.credentials.removeprefix("test:")


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
def api_key_repository() -> InMemoryApiKeyRepository:
    return InMemoryApiKeyRepository()


@pytest.fixture
def user_repository() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def client(
    conversation_store: ConversationStore,
    pattern_repository: IntentPatternRepository,
    embedding_provider: EmbeddingProvider,
    answered_question_repository: AnsweredQuestionRepository,
    business_settings_repository: BusinessSettingsRepository,
    decision_repository: DecisionRepository,
    company_repository: CompanyRepository,
    api_key_repository: ApiKeyRepository,
    user_repository: InMemoryUserRepository,
) -> Iterator[TestClient]:
    """API test client backed by isolated in-memory/fake stores.

    Unit/API tests must not depend on a developer-local PostgreSQL instance
    or the real (large) embedding model - see the *_postgres.py integration
    test files for real-DB coverage. Tests that need business-specific
    custom intent patterns, controlled embedding similarity, non-default
    knowledge-scope/TTL settings, or to inspect recorded decisions can
    additionally request the corresponding fixture to seed or inspect it.

    get_authenticated_tenant_id is overridden to a test-only fake that
    trusts 'Bearer test:<tenant_id>' directly (see
    _fake_authenticated_tenant_id) - no real key ever needs to be minted.
    Tests exercising the *real* auth dependency should use
    `client_with_real_auth` instead.
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

    async def _get_test_api_keys() -> ApiKeyRepository:
        return api_key_repository

    async def _get_test_users() -> InMemoryUserRepository:
        return user_repository

    app.dependency_overrides[get_conversation_store] = _get_test_store
    app.dependency_overrides[get_intent_pattern_repository] = _get_test_patterns
    app.dependency_overrides[get_embedding_provider] = _get_test_embeddings
    app.dependency_overrides[get_answered_question_repository] = _get_test_answered_questions
    app.dependency_overrides[get_business_settings_repository] = _get_test_business_settings
    app.dependency_overrides[get_decision_repository] = _get_test_decisions
    app.dependency_overrides[get_company_repository] = _get_test_companies
    app.dependency_overrides[get_api_key_repository] = _get_test_api_keys
    app.dependency_overrides[get_user_repository] = _get_test_users
    app.dependency_overrides[get_authenticated_tenant_id] = _fake_authenticated_tenant_id
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
        del app.dependency_overrides[get_api_key_repository]
        del app.dependency_overrides[get_user_repository]
        del app.dependency_overrides[get_authenticated_tenant_id]


@pytest.fixture
async def authenticated_client(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> AsyncIterator[tuple[TestClient, User]]:
    """Like `client`, but with a fake signed-in human user - overrides
    get_current_user_or_none directly (the shared sub-dependency behind
    both require_current_user_for_page and require_current_user_for_api)
    rather than going through a real OAuth login + session cookie, which
    would need a live provider. Yields (client, user)."""

    user = await user_repository.create(
        email="test@example.com", provider="google", subject="test-sub"
    )

    async def _fake_current_user() -> User:
        return user

    app.dependency_overrides[get_current_user_or_none] = _fake_current_user
    try:
        yield client, user
    finally:
        del app.dependency_overrides[get_current_user_or_none]


@pytest.fixture
def client_with_real_auth(
    conversation_store: ConversationStore,
    pattern_repository: IntentPatternRepository,
    embedding_provider: EmbeddingProvider,
    answered_question_repository: AnsweredQuestionRepository,
    business_settings_repository: BusinessSettingsRepository,
    decision_repository: DecisionRepository,
    company_repository: CompanyRepository,
    api_key_repository: ApiKeyRepository,
) -> Iterator[TestClient]:
    """Like `client`, but does NOT override get_authenticated_tenant_id -
    the real hash-and-lookup dependency runs, against the same in-memory
    api_key_repository fixture. Use this to test the auth dependency
    itself, or to prove a key minted by POST /v1/companies genuinely
    authenticates - the `Bearer test:` shortcut every other test uses
    would not exercise either of those.
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

    async def _get_test_api_keys() -> ApiKeyRepository:
        return api_key_repository

    app.dependency_overrides[get_conversation_store] = _get_test_store
    app.dependency_overrides[get_intent_pattern_repository] = _get_test_patterns
    app.dependency_overrides[get_embedding_provider] = _get_test_embeddings
    app.dependency_overrides[get_answered_question_repository] = _get_test_answered_questions
    app.dependency_overrides[get_business_settings_repository] = _get_test_business_settings
    app.dependency_overrides[get_decision_repository] = _get_test_decisions
    app.dependency_overrides[get_company_repository] = _get_test_companies
    app.dependency_overrides[get_api_key_repository] = _get_test_api_keys
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
        del app.dependency_overrides[get_api_key_repository]


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
