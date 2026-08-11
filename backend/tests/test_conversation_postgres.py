from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.conversation.scope import ConversationScope
from backend.app.infrastructure.conversation.postgres import PostgresConversationStore
from backend.app.models.business import Business
from backend.app.models.conversation_message import ConversationMessageModel
from backend.app.models.tenant import Tenant


async def _create_tenant_and_business(session: AsyncSession) -> tuple[str, str]:
    """Insert a Tenant/Business pair the conversation_messages FKs can reference.

    Not committed - the enclosing db_session transaction is rolled back on
    teardown, so this never persists beyond a single test.
    """
    tenant = Tenant(name="Test Tenant", slug=f"test-tenant-{uuid4()}")
    session.add(tenant)
    await session.flush()

    business = Business(tenant_id=tenant.id, name="Test Business", slug=f"test-business-{uuid4()}")
    session.add(business)
    await session.flush()

    return str(tenant.id), str(business.id)


async def test_save_and_get_last_assistant_response(db_session: AsyncSession) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    store = PostgresConversationStore(db_session)
    scope = ConversationScope(
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id="conversation-1",
    )

    await store.save_assistant_response(scope=scope, text="Hello! How can I help you?")

    last_response = await store.get_last_assistant_response(scope=scope)

    assert last_response is not None
    assert last_response.text == "Hello! How can I help you?"
    assert last_response.role == "assistant"
    assert last_response.conversation_id == "conversation-1"


async def test_get_last_assistant_response_returns_none_when_empty(
    db_session: AsyncSession,
) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    store = PostgresConversationStore(db_session)
    scope = ConversationScope(
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id="conversation-without-history",
    )

    last_response = await store.get_last_assistant_response(scope=scope)

    assert last_response is None


async def test_get_last_assistant_response_returns_most_recent(
    db_session: AsyncSession,
) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    store = PostgresConversationStore(db_session)
    scope = ConversationScope(
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id="conversation-1",
    )

    await store.save_assistant_response(scope=scope, text="First response")
    await store.save_assistant_response(scope=scope, text="Second response")

    last_response = await store.get_last_assistant_response(scope=scope)

    assert last_response is not None
    assert last_response.text == "Second response"


async def test_save_user_message(db_session: AsyncSession) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    store = PostgresConversationStore(db_session)
    scope = ConversationScope(
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id="conversation-1",
    )

    await store.save_user_message(scope=scope, text="Hello")

    recent = await store.get_recent_messages(scope=scope)

    assert len(recent) == 1
    assert recent[0].role == "user"
    assert recent[0].text == "Hello"


async def test_get_recent_messages_interleaves_user_and_assistant_turns(
    db_session: AsyncSession,
) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    store = PostgresConversationStore(db_session)
    scope = ConversationScope(
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id="conversation-1",
    )

    await store.save_user_message(scope=scope, text="Hello")
    await store.save_assistant_response(scope=scope, text="Hi! How can I help you?")
    await store.save_user_message(scope=scope, text="What is your refund policy?")

    recent = await store.get_recent_messages(scope=scope)

    assert [(message.role, message.text) for message in recent] == [
        ("user", "Hello"),
        ("assistant", "Hi! How can I help you?"),
        ("user", "What is your refund policy?"),
    ]


async def test_get_recent_messages_returns_oldest_first_up_to_limit(
    db_session: AsyncSession,
) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    store = PostgresConversationStore(db_session)
    scope = ConversationScope(
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id="conversation-1",
    )

    for i in range(5):
        await store.save_assistant_response(scope=scope, text=f"response-{i}")

    recent = await store.get_recent_messages(scope=scope, limit=3)

    assert [message.text for message in recent] == ["response-2", "response-3", "response-4"]


async def test_conversation_id_isolation(db_session: AsyncSession) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    store = PostgresConversationStore(db_session)

    scope_a = ConversationScope(
        tenant_id=tenant_id, business_id=business_id, conversation_id="conversation-a"
    )
    scope_b = ConversationScope(
        tenant_id=tenant_id, business_id=business_id, conversation_id="conversation-b"
    )

    await store.save_assistant_response(scope=scope_a, text="Response for A")

    last_for_b = await store.get_last_assistant_response(scope=scope_b)

    assert last_for_b is None


async def test_tenant_isolation(db_session: AsyncSession) -> None:
    tenant_id_a, business_id = await _create_tenant_and_business(db_session)
    tenant_id_b, _ = await _create_tenant_and_business(db_session)
    store = PostgresConversationStore(db_session)

    scope_a = ConversationScope(
        tenant_id=tenant_id_a, business_id=business_id, conversation_id="shared-conversation"
    )
    scope_b = ConversationScope(
        tenant_id=tenant_id_b, business_id=business_id, conversation_id="shared-conversation"
    )

    await store.save_assistant_response(scope=scope_a, text="Response for tenant A")

    last_for_b = await store.get_last_assistant_response(scope=scope_b)

    assert last_for_b is None


async def test_business_isolation(db_session: AsyncSession) -> None:
    tenant_id, business_id_a = await _create_tenant_and_business(db_session)
    _, business_id_b = await _create_tenant_and_business(db_session)
    store = PostgresConversationStore(db_session)

    scope_a = ConversationScope(
        tenant_id=tenant_id, business_id=business_id_a, conversation_id="shared-conversation"
    )
    scope_b = ConversationScope(
        tenant_id=tenant_id, business_id=business_id_b, conversation_id="shared-conversation"
    )

    await store.save_assistant_response(scope=scope_a, text="Response for business A")

    last_for_b = await store.get_last_assistant_response(scope=scope_b)

    assert last_for_b is None


async def _backdate(db_session: AsyncSession, text: str, created_at: datetime) -> None:
    await db_session.execute(
        update(ConversationMessageModel)
        .where(ConversationMessageModel.text == text)
        .values(created_at=created_at)
    )
    await db_session.flush()


async def test_purge_expired_deletes_old_messages_but_keeps_recent(
    db_session: AsyncSession,
) -> None:
    """purge_expired is deliberately global (every tenant/business), so this
    only asserts on this test's own scope - a real dev database can have
    other legitimate data in the table that this must not assume away."""

    tenant_id, business_id = await _create_tenant_and_business(db_session)
    store = PostgresConversationStore(db_session)
    scope = ConversationScope(
        tenant_id=tenant_id, business_id=business_id, conversation_id="conversation-1"
    )

    await store.save_assistant_response(scope=scope, text="Old message")
    await store.save_assistant_response(scope=scope, text="Recent message")
    await _backdate(db_session, "Old message", datetime.now(UTC) - timedelta(days=100))

    deleted = await store.purge_expired(older_than=datetime.now(UTC) - timedelta(days=50))

    assert deleted >= 1
    remaining = await store.get_recent_messages(scope=scope)
    assert [message.text for message in remaining] == ["Recent message"]


async def test_purge_expired_is_not_scoped_to_a_single_business(
    db_session: AsyncSession,
) -> None:
    tenant_id, business_id_a = await _create_tenant_and_business(db_session)
    _, business_id_b = await _create_tenant_and_business(db_session)
    store = PostgresConversationStore(db_session)

    scope_a = ConversationScope(
        tenant_id=tenant_id, business_id=business_id_a, conversation_id="conversation-a"
    )
    scope_b = ConversationScope(
        tenant_id=tenant_id, business_id=business_id_b, conversation_id="conversation-b"
    )

    await store.save_assistant_response(scope=scope_a, text="Old message A")
    await store.save_assistant_response(scope=scope_b, text="Old message B")
    old_timestamp = datetime.now(UTC) - timedelta(days=100)
    await _backdate(db_session, "Old message A", old_timestamp)
    await _backdate(db_session, "Old message B", old_timestamp)

    deleted = await store.purge_expired(older_than=datetime.now(UTC) - timedelta(days=50))

    assert deleted >= 2
    assert await store.get_last_assistant_response(scope=scope_a) is None
    assert await store.get_last_assistant_response(scope=scope_b) is None
