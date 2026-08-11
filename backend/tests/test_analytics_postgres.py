from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.analytics.decision_record import DecisionRecord
from backend.app.domain.inference import InferenceAction
from backend.app.infrastructure.analytics.postgres import PostgresDecisionRepository
from backend.app.models.business import Business
from backend.app.models.tenant import Tenant


async def _create_tenant_and_business(session: AsyncSession) -> tuple[str, str]:
    """Insert a Tenant/Business pair the decision_log FKs can reference.

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


def _record(
    tenant_id: str,
    business_id: str,
    action: InferenceAction,
    source: str | None,
    conversation_id: str = "conversation-1",
    similarity: float | None = None,
    matched_question: str | None = None,
) -> DecisionRecord:
    return DecisionRecord(
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id=conversation_id,
        agent_id="default",
        action=action,
        source=source,
        intent=None,
        similarity=similarity,
        matched_question=matched_question,
        latency_ms=1.5,
        created_at=datetime.now(UTC),
    )


async def test_summarize_returns_zeroed_summary_when_empty(db_session: AsyncSession) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    repository = PostgresDecisionRepository(db_session)

    summary = await repository.summarize(tenant_id=tenant_id, business_id=business_id)

    assert summary.total == 0
    assert summary.respond_count == 0
    assert summary.fallback_count == 0
    assert summary.respond_by_source == {}


async def test_summarize_counts_by_action_and_source(db_session: AsyncSession) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    repository = PostgresDecisionRepository(db_session)

    await repository.record(
        _record(tenant_id, business_id, InferenceAction.RESPOND, "builtin:greeting")
    )
    await repository.record(
        _record(tenant_id, business_id, InferenceAction.RESPOND, "builtin:greeting")
    )
    await repository.record(
        _record(tenant_id, business_id, InferenceAction.RESPOND, "knowledge:semantic_match")
    )
    await repository.record(_record(tenant_id, business_id, InferenceAction.FALLBACK, None))

    summary = await repository.summarize(tenant_id=tenant_id, business_id=business_id)

    assert summary.total == 4
    assert summary.respond_count == 3
    assert summary.fallback_count == 1
    assert summary.respond_by_source == {
        "builtin:greeting": 2,
        "knowledge:semantic_match": 1,
    }
    assert summary.avoided_llm_rate == 0.75


async def test_summarize_is_isolated_to_its_business(db_session: AsyncSession) -> None:
    tenant_id, business_id_a = await _create_tenant_and_business(db_session)
    _, business_id_b = await _create_tenant_and_business(db_session)
    repository = PostgresDecisionRepository(db_session)

    await repository.record(
        _record(tenant_id, business_id_a, InferenceAction.RESPOND, "builtin:greeting")
    )

    summary = await repository.summarize(tenant_id=tenant_id, business_id=business_id_b)

    assert summary.total == 0


async def test_list_for_conversation_returns_oldest_first_with_similarity_fields(
    db_session: AsyncSession,
) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    repository = PostgresDecisionRepository(db_session)

    await repository.record(
        _record(
            tenant_id,
            business_id,
            InferenceAction.FALLBACK,
            None,
            conversation_id="conversation-history",
            similarity=0.6,
            matched_question="an unrelated earlier question",
        )
    )
    await repository.record(
        _record(
            tenant_id,
            business_id,
            InferenceAction.RESPOND,
            "knowledge:semantic_match",
            conversation_id="conversation-history",
            similarity=0.95,
            matched_question="do you accept delta dental",
        )
    )

    decisions = await repository.list_for_conversation(
        tenant_id=tenant_id, business_id=business_id, conversation_id="conversation-history"
    )

    assert [d.action for d in decisions] == [InferenceAction.FALLBACK, InferenceAction.RESPOND]
    assert decisions[1].similarity == 0.95
    assert decisions[1].matched_question == "do you accept delta dental"


async def test_list_for_conversation_is_isolated_to_its_conversation(
    db_session: AsyncSession,
) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    repository = PostgresDecisionRepository(db_session)

    await repository.record(
        _record(
            tenant_id,
            business_id,
            InferenceAction.RESPOND,
            "builtin:greeting",
            conversation_id="conversation-a",
        )
    )

    decisions = await repository.list_for_conversation(
        tenant_id=tenant_id, business_id=business_id, conversation_id="conversation-b"
    )

    assert decisions == []
