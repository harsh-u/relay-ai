from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.knowledge.postgres import PostgresAnsweredQuestionRepository
from backend.app.models.answered_question import AnsweredQuestionModel
from backend.app.models.business import Business
from backend.app.models.tenant import Tenant

_DIM = 768
_FAR_PAST = datetime(2000, 1, 1, tzinfo=UTC)


def _vector(*values: float) -> list[float]:
    padded = list(values) + [0.0] * (_DIM - len(values))
    return padded[:_DIM]


async def _create_tenant_and_business(session: AsyncSession) -> tuple[str, str]:
    """Insert a Tenant/Business pair the answered_questions FKs can reference.

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


async def test_find_most_similar_returns_none_when_empty(db_session: AsyncSession) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    repository = PostgresAnsweredQuestionRepository(db_session)

    result = await repository.find_most_similar(
        tenant_id=tenant_id,
        business_id=business_id,
        agent_id=None,
        embedding=_vector(1.0),
        min_created_at=_FAR_PAST,
    )

    assert result is None


async def test_save_and_find_most_similar(db_session: AsyncSession) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    repository = PostgresAnsweredQuestionRepository(db_session)

    await repository.save(
        tenant_id=tenant_id,
        business_id=business_id,
        agent_id="agent-1",
        question="Do you accept Delta Dental insurance?",
        answer="Yes, we're in-network with Delta Dental PPO.",
        embedding=_vector(1.0, 0.0, 0.0),
        dedup_similarity_threshold=0.75,
    )

    result = await repository.find_most_similar(
        tenant_id=tenant_id,
        business_id=business_id,
        agent_id=None,
        embedding=_vector(1.0, 0.0, 0.0),
        min_created_at=_FAR_PAST,
    )

    assert result is not None
    answered_question, similarity = result
    assert answered_question.question == "Do you accept Delta Dental insurance?"
    assert answered_question.answer == "Yes, we're in-network with Delta Dental PPO."
    assert similarity > 0.999


async def test_find_most_similar_returns_closest_of_several(db_session: AsyncSession) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    repository = PostgresAnsweredQuestionRepository(db_session)

    await repository.save(
        tenant_id=tenant_id,
        business_id=business_id,
        agent_id="agent-1",
        question="Do you accept Delta Dental insurance?",
        answer="Yes, we're in-network with Delta Dental PPO.",
        embedding=_vector(1.0, 0.0, 0.0),
        dedup_similarity_threshold=0.75,
    )
    await repository.save(
        tenant_id=tenant_id,
        business_id=business_id,
        agent_id="agent-1",
        question="What time do you close on Saturdays?",
        answer="We close at 2pm on Saturdays.",
        embedding=_vector(0.0, 1.0, 0.0),
        dedup_similarity_threshold=0.75,
    )

    result = await repository.find_most_similar(
        tenant_id=tenant_id,
        business_id=business_id,
        agent_id=None,
        embedding=_vector(0.9, 0.1, 0.0),
        min_created_at=_FAR_PAST,
    )

    assert result is not None
    answered_question, _ = result
    assert answered_question.question == "Do you accept Delta Dental insurance?"


async def test_business_isolation(db_session: AsyncSession) -> None:
    tenant_id, business_id_a = await _create_tenant_and_business(db_session)
    _, business_id_b = await _create_tenant_and_business(db_session)
    repository = PostgresAnsweredQuestionRepository(db_session)

    await repository.save(
        tenant_id=tenant_id,
        business_id=business_id_a,
        agent_id="agent-1",
        question="Do you accept Delta Dental insurance?",
        answer="Yes, we're in-network with Delta Dental PPO.",
        embedding=_vector(1.0, 0.0, 0.0),
        dedup_similarity_threshold=0.75,
    )

    result = await repository.find_most_similar(
        tenant_id=tenant_id,
        business_id=business_id_b,
        agent_id=None,
        embedding=_vector(1.0, 0.0, 0.0),
        min_created_at=_FAR_PAST,
    )

    assert result is None


async def test_tenant_isolation(db_session: AsyncSession) -> None:
    tenant_id_a, business_id = await _create_tenant_and_business(db_session)
    tenant_id_b, _ = await _create_tenant_and_business(db_session)
    repository = PostgresAnsweredQuestionRepository(db_session)

    await repository.save(
        tenant_id=tenant_id_a,
        business_id=business_id,
        agent_id="agent-1",
        question="Do you accept Delta Dental insurance?",
        answer="Yes, we're in-network with Delta Dental PPO.",
        embedding=_vector(1.0, 0.0, 0.0),
        dedup_similarity_threshold=0.75,
    )

    result = await repository.find_most_similar(
        tenant_id=tenant_id_b,
        business_id=business_id,
        agent_id=None,
        embedding=_vector(1.0, 0.0, 0.0),
        min_created_at=_FAR_PAST,
    )

    assert result is None


async def test_agent_isolation_when_agent_id_given(db_session: AsyncSession) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    repository = PostgresAnsweredQuestionRepository(db_session)

    await repository.save(
        tenant_id=tenant_id,
        business_id=business_id,
        agent_id="agent-a",
        question="Do you accept Delta Dental insurance?",
        answer="Yes, we're in-network with Delta Dental PPO.",
        embedding=_vector(1.0, 0.0, 0.0),
        dedup_similarity_threshold=0.75,
    )

    result_for_other_agent = await repository.find_most_similar(
        tenant_id=tenant_id,
        business_id=business_id,
        agent_id="agent-b",
        embedding=_vector(1.0, 0.0, 0.0),
        min_created_at=_FAR_PAST,
    )
    result_for_same_agent = await repository.find_most_similar(
        tenant_id=tenant_id,
        business_id=business_id,
        agent_id="agent-a",
        embedding=_vector(1.0, 0.0, 0.0),
        min_created_at=_FAR_PAST,
    )
    result_shared = await repository.find_most_similar(
        tenant_id=tenant_id,
        business_id=business_id,
        agent_id=None,
        embedding=_vector(1.0, 0.0, 0.0),
        min_created_at=_FAR_PAST,
    )

    assert result_for_other_agent is None
    assert result_for_same_agent is not None
    assert result_shared is not None


async def test_min_created_at_excludes_stale_entries(db_session: AsyncSession) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    repository = PostgresAnsweredQuestionRepository(db_session)

    stale_row = AnsweredQuestionModel(
        tenant_id=UUID(tenant_id),
        business_id=UUID(business_id),
        agent_id="agent-1",
        question="What is your return policy?",
        answer="30 days, no receipt needed.",
        embedding=_vector(1.0, 0.0, 0.0),
        created_at=datetime.now(UTC) - timedelta(days=90),
    )
    db_session.add(stale_row)
    await db_session.flush()

    result = await repository.find_most_similar(
        tenant_id=tenant_id,
        business_id=business_id,
        agent_id=None,
        embedding=_vector(1.0, 0.0, 0.0),
        min_created_at=datetime.now(UTC) - timedelta(days=30),
    )

    assert result is None


async def test_clear_deletes_all_for_business_when_no_agent_given(db_session: AsyncSession) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    repository = PostgresAnsweredQuestionRepository(db_session)

    await repository.save(
        tenant_id=tenant_id,
        business_id=business_id,
        agent_id="agent-a",
        question="Do you accept Delta Dental insurance?",
        answer="Yes.",
        embedding=_vector(1.0, 0.0, 0.0),
        dedup_similarity_threshold=0.75,
    )
    await repository.save(
        tenant_id=tenant_id,
        business_id=business_id,
        agent_id="agent-b",
        question="What are your hours?",
        answer="9 to 5.",
        embedding=_vector(0.0, 1.0, 0.0),
        dedup_similarity_threshold=0.75,
    )

    deleted = await repository.clear(tenant_id=tenant_id, business_id=business_id, agent_id=None)

    assert deleted == 2

    result = await repository.find_most_similar(
        tenant_id=tenant_id,
        business_id=business_id,
        agent_id=None,
        embedding=_vector(1.0, 0.0, 0.0),
        min_created_at=_FAR_PAST,
    )
    assert result is None


async def test_clear_only_deletes_given_agent(db_session: AsyncSession) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    repository = PostgresAnsweredQuestionRepository(db_session)

    await repository.save(
        tenant_id=tenant_id,
        business_id=business_id,
        agent_id="agent-a",
        question="Do you accept Delta Dental insurance?",
        answer="Yes.",
        embedding=_vector(1.0, 0.0, 0.0),
        dedup_similarity_threshold=0.75,
    )
    await repository.save(
        tenant_id=tenant_id,
        business_id=business_id,
        agent_id="agent-b",
        question="What are your hours?",
        answer="9 to 5.",
        embedding=_vector(0.0, 1.0, 0.0),
        dedup_similarity_threshold=0.75,
    )

    deleted = await repository.clear(
        tenant_id=tenant_id, business_id=business_id, agent_id="agent-a"
    )

    assert deleted == 1

    remaining_for_b = await repository.find_most_similar(
        tenant_id=tenant_id,
        business_id=business_id,
        agent_id="agent-b",
        embedding=_vector(0.0, 1.0, 0.0),
        min_created_at=_FAR_PAST,
    )
    assert remaining_for_b is not None


async def _row_count(db_session: AsyncSession, tenant_id: str, business_id: str) -> int:
    statement = select(func.count()).where(
        AnsweredQuestionModel.tenant_id == UUID(tenant_id),
        AnsweredQuestionModel.business_id == UUID(business_id),
    )
    result = await db_session.execute(statement)
    return result.scalar_one()


async def test_dedup_updates_existing_row_instead_of_inserting_a_new_one(
    db_session: AsyncSession,
) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    repository = PostgresAnsweredQuestionRepository(db_session)

    await repository.save(
        tenant_id=tenant_id,
        business_id=business_id,
        agent_id="agent-1",
        question="Do you accept Delta Dental insurance?",
        answer="Yes, we accept Delta Dental PPO.",
        embedding=_vector(1.0, 0.0, 0.0),
        dedup_similarity_threshold=0.75,
    )
    await repository.save(
        tenant_id=tenant_id,
        business_id=business_id,
        agent_id="agent-1",
        question="Is Delta Dental accepted here?",
        answer="Yes, we accept Delta Dental PPO and HMO.",
        embedding=_vector(0.99, 0.01, 0.0),
        dedup_similarity_threshold=0.75,
    )

    assert await _row_count(db_session, tenant_id, business_id) == 1

    result = await repository.find_most_similar(
        tenant_id=tenant_id,
        business_id=business_id,
        agent_id="agent-1",
        embedding=_vector(1.0, 0.0, 0.0),
        min_created_at=_FAR_PAST,
    )
    assert result is not None
    answered_question, _ = result
    assert answered_question.question == "Is Delta Dental accepted here?"
    assert answered_question.answer == "Yes, we accept Delta Dental PPO and HMO."


async def test_dissimilar_questions_are_not_deduped(db_session: AsyncSession) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    repository = PostgresAnsweredQuestionRepository(db_session)

    await repository.save(
        tenant_id=tenant_id,
        business_id=business_id,
        agent_id="agent-1",
        question="Do you accept Delta Dental insurance?",
        answer="Yes.",
        embedding=_vector(1.0, 0.0, 0.0),
        dedup_similarity_threshold=0.75,
    )
    await repository.save(
        tenant_id=tenant_id,
        business_id=business_id,
        agent_id="agent-1",
        question="What time do you close on Saturdays?",
        answer="2pm.",
        embedding=_vector(0.0, 1.0, 0.0),
        dedup_similarity_threshold=0.75,
    )

    assert await _row_count(db_session, tenant_id, business_id) == 2


async def test_dedup_does_not_cross_agents(db_session: AsyncSession) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    repository = PostgresAnsweredQuestionRepository(db_session)

    await repository.save(
        tenant_id=tenant_id,
        business_id=business_id,
        agent_id="agent-a",
        question="Do you accept Delta Dental insurance?",
        answer="Yes.",
        embedding=_vector(1.0, 0.0, 0.0),
        dedup_similarity_threshold=0.75,
    )
    await repository.save(
        tenant_id=tenant_id,
        business_id=business_id,
        agent_id="agent-b",
        question="Is Delta Dental accepted here?",
        answer="Yes.",
        embedding=_vector(0.99, 0.01, 0.0),
        dedup_similarity_threshold=0.75,
    )

    assert await _row_count(db_session, tenant_id, business_id) == 2
