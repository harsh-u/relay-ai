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
