import uuid

from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.auth.postgres import PostgresApiKeyRepository
from backend.app.main import app
from backend.app.models.business import Business
from backend.app.models.conversation_message import ConversationMessageModel
from backend.app.models.tenant import Tenant


async def test_conversation_writes_persist_across_separate_requests(
    db_session: AsyncSession,
) -> None:
    """Regression test: get_db_session() must commit, or writes from one
    HTTP request are invisible to the next - this silently broke all
    Postgres conversation persistence in the real running app. It was
    masked everywhere else: fast API tests use an in-memory override, and
    the Postgres integration tests share one transaction across calls
    within a single test function, so neither ever exercised "does a write
    survive past the request that made it."

    Deliberately does not use the `client` fixture (in-memory override) or
    the sync `TestClient` (its sync-to-async bridging can itself introduce a
    second event loop across sequential calls - the same class of bug this
    test is guarding against, just from a different source). An async ASGI
    transport keeps the whole test on one event loop throughout.
    """

    tenant = Tenant(name="Commit Regression Tenant", slug=f"commit-regression-{uuid.uuid4()}")
    db_session.add(tenant)
    await db_session.flush()

    business = Business(
        tenant_id=tenant.id,
        name="Commit Regression Business",
        slug=f"commit-regression-{uuid.uuid4()}",
    )
    db_session.add(business)
    await db_session.flush()

    _, raw_api_key = await PostgresApiKeyRepository(db_session).create(tenant_id=str(tenant.id))
    await db_session.commit()

    business_id = str(business.id)
    conversation_id = f"commit-regression-{uuid.uuid4()}"
    headers = {"Authorization": f"Bearer {raw_api_key}"}

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post(
                f"/v1/conversations/{conversation_id}/messages",
                json={
                    "business_id": business_id,
                    "text": "Persisted answer",
                },
                headers=headers,
            )

            response = await client.post(
                "/v1/inference",
                json={
                    "business_id": business_id,
                    "conversation_id": conversation_id,
                    "text": "Can you repeat that?",
                },
                headers=headers,
            )

        assert response.json() == {
            "action": "respond",
            "text": "Persisted answer",
            "source": "conversation:last_response",
            "intent": "repeat_request",
            "similarity": None,
            "matched_question": None,
        }
    finally:
        await db_session.execute(
            delete(ConversationMessageModel).where(
                ConversationMessageModel.conversation_id == conversation_id
            )
        )
        await db_session.execute(delete(Business).where(Business.id == business.id))
        await db_session.execute(delete(Tenant).where(Tenant.id == tenant.id))
        await db_session.commit()
