from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.knowledge.postgres import PostgresAnsweredQuestionRepository
from backend.app.models.business import Business
from backend.app.models.tenant import Tenant

_DIM = 768


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
        embedding=_vector(1.0),
    )

    assert result is None


async def test_save_and_find_most_similar(db_session: AsyncSession) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    repository = PostgresAnsweredQuestionRepository(db_session)

    await repository.save(
        tenant_id=tenant_id,
        business_id=business_id,
        question="Do you accept Delta Dental insurance?",
        answer="Yes, we're in-network with Delta Dental PPO.",
        embedding=_vector(1.0, 0.0, 0.0),
    )

    result = await repository.find_most_similar(
        tenant_id=tenant_id,
        business_id=business_id,
        embedding=_vector(1.0, 0.0, 0.0),
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
        question="Do you accept Delta Dental insurance?",
        answer="Yes, we're in-network with Delta Dental PPO.",
        embedding=_vector(1.0, 0.0, 0.0),
    )
    await repository.save(
        tenant_id=tenant_id,
        business_id=business_id,
        question="What time do you close on Saturdays?",
        answer="We close at 2pm on Saturdays.",
        embedding=_vector(0.0, 1.0, 0.0),
    )

    result = await repository.find_most_similar(
        tenant_id=tenant_id,
        business_id=business_id,
        embedding=_vector(0.9, 0.1, 0.0),
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
        question="Do you accept Delta Dental insurance?",
        answer="Yes, we're in-network with Delta Dental PPO.",
        embedding=_vector(1.0, 0.0, 0.0),
    )

    result = await repository.find_most_similar(
        tenant_id=tenant_id,
        business_id=business_id_b,
        embedding=_vector(1.0, 0.0, 0.0),
    )

    assert result is None


async def test_tenant_isolation(db_session: AsyncSession) -> None:
    tenant_id_a, business_id = await _create_tenant_and_business(db_session)
    tenant_id_b, _ = await _create_tenant_and_business(db_session)
    repository = PostgresAnsweredQuestionRepository(db_session)

    await repository.save(
        tenant_id=tenant_id_a,
        business_id=business_id,
        question="Do you accept Delta Dental insurance?",
        answer="Yes, we're in-network with Delta Dental PPO.",
        embedding=_vector(1.0, 0.0, 0.0),
    )

    result = await repository.find_most_similar(
        tenant_id=tenant_id_b,
        business_id=business_id,
        embedding=_vector(1.0, 0.0, 0.0),
    )

    assert result is None
