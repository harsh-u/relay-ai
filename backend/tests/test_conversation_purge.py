from dataclasses import replace
from datetime import UTC, datetime, timedelta

from backend.app.domain.conversation.scope import ConversationScope
from backend.app.infrastructure.conversation.in_memory import InMemoryConversationStore

TENANT_ID = "tenant-1"
BUSINESS_ID = "business-1"


async def test_purge_expired_deletes_old_messages_but_keeps_recent() -> None:
    store = InMemoryConversationStore()
    scope = ConversationScope(
        tenant_id=TENANT_ID, business_id=BUSINESS_ID, conversation_id="conversation-1"
    )

    await store.save_assistant_response(scope=scope, text="Old message")
    await store.save_assistant_response(scope=scope, text="Recent message")

    old_message = store._messages[scope.key][0]
    store._messages[scope.key][0] = replace(
        old_message, created_at=datetime.now(UTC) - timedelta(days=3)
    )

    deleted = await store.purge_expired(older_than=datetime.now(UTC) - timedelta(days=1))

    assert deleted == 1
    remaining = await store.get_recent_messages(scope=scope)
    assert [message.text for message in remaining] == ["Recent message"]


async def test_purge_expired_deletes_nothing_when_everything_is_recent() -> None:
    store = InMemoryConversationStore()
    scope = ConversationScope(
        tenant_id=TENANT_ID, business_id=BUSINESS_ID, conversation_id="conversation-1"
    )

    await store.save_assistant_response(scope=scope, text="Recent message")

    deleted = await store.purge_expired(older_than=datetime.now(UTC) - timedelta(days=1))

    assert deleted == 0
    remaining = await store.get_recent_messages(scope=scope)
    assert len(remaining) == 1


async def test_list_recent_conversations_shows_the_last_message_per_conversation() -> None:
    store = InMemoryConversationStore()
    scope_a = ConversationScope(
        tenant_id=TENANT_ID, business_id=BUSINESS_ID, conversation_id="conversation-a"
    )
    scope_b = ConversationScope(
        tenant_id=TENANT_ID, business_id=BUSINESS_ID, conversation_id="conversation-b"
    )

    await store.save_user_message(scope=scope_a, text="Hi")
    await store.save_assistant_response(scope=scope_a, text="Hello! How can I help you?")
    await store.save_user_message(scope=scope_b, text="What are your hours?")

    summaries = await store.list_recent_conversations(tenant_id=TENANT_ID, business_id=BUSINESS_ID)

    by_id = {summary.conversation_id: summary for summary in summaries}
    assert set(by_id) == {"conversation-a", "conversation-b"}
    assert by_id["conversation-a"].last_message_role == "assistant"
    assert by_id["conversation-a"].last_message_text == "Hello! How can I help you?"
    assert by_id["conversation-b"].last_message_role == "user"
    assert by_id["conversation-b"].last_message_text == "What are your hours?"


async def test_list_recent_conversations_orders_by_most_recent_activity() -> None:
    store = InMemoryConversationStore()
    scope_older = ConversationScope(
        tenant_id=TENANT_ID, business_id=BUSINESS_ID, conversation_id="conversation-older"
    )
    scope_newer = ConversationScope(
        tenant_id=TENANT_ID, business_id=BUSINESS_ID, conversation_id="conversation-newer"
    )

    await store.save_user_message(scope=scope_older, text="First conversation")
    older_message = store._messages[scope_older.key][0]
    store._messages[scope_older.key][0] = replace(
        older_message, created_at=datetime.now(UTC) - timedelta(minutes=5)
    )
    await store.save_user_message(scope=scope_newer, text="Second conversation")

    summaries = await store.list_recent_conversations(tenant_id=TENANT_ID, business_id=BUSINESS_ID)

    assert [summary.conversation_id for summary in summaries] == [
        "conversation-newer",
        "conversation-older",
    ]


async def test_list_recent_conversations_respects_the_limit() -> None:
    store = InMemoryConversationStore()

    for i in range(5):
        scope = ConversationScope(
            tenant_id=TENANT_ID, business_id=BUSINESS_ID, conversation_id=f"conversation-{i}"
        )
        await store.save_user_message(scope=scope, text=f"Message {i}")

    summaries = await store.list_recent_conversations(
        tenant_id=TENANT_ID, business_id=BUSINESS_ID, limit=2
    )

    assert len(summaries) == 2


async def test_list_recent_conversations_is_scoped_to_its_business() -> None:
    store = InMemoryConversationStore()
    scope = ConversationScope(
        tenant_id=TENANT_ID, business_id=BUSINESS_ID, conversation_id="conversation-a"
    )
    await store.save_user_message(scope=scope, text="Hi")

    summaries = await store.list_recent_conversations(tenant_id=TENANT_ID, business_id="business-2")

    assert summaries == []
