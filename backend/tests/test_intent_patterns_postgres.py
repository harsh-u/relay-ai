from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.matching.builtin_patterns import BUILTIN_PATTERNS
from backend.app.domain.matching.intent import Intent
from backend.app.infrastructure.matching.postgres_patterns import (
    PostgresIntentPatternRepository,
)
from backend.app.models.business import Business
from backend.app.models.intent_pattern import IntentPatternModel
from backend.app.models.tenant import Tenant


async def _create_tenant_and_business(session: AsyncSession) -> tuple[str, str]:
    """Insert a Tenant/Business pair the intent_patterns FKs can reference.

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


async def test_returns_builtin_patterns_when_no_custom_patterns_exist(
    db_session: AsyncSession,
) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    repository = PostgresIntentPatternRepository(db_session)

    patterns = await repository.get_patterns(tenant_id=tenant_id, business_id=business_id)

    assert patterns == BUILTIN_PATTERNS


async def test_custom_pattern_is_merged_with_builtin_patterns(db_session: AsyncSession) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    db_session.add(
        IntentPatternModel(
            tenant_id=tenant_id,
            business_id=business_id,
            intent=Intent.GREETING.value,
            pattern="yo",
        )
    )
    await db_session.flush()

    repository = PostgresIntentPatternRepository(db_session)
    patterns = await repository.get_patterns(tenant_id=tenant_id, business_id=business_id)

    assert "yo" in patterns[Intent.GREETING]
    for builtin_pattern in BUILTIN_PATTERNS[Intent.GREETING]:
        assert builtin_pattern in patterns[Intent.GREETING]


async def test_custom_pattern_is_isolated_to_its_business(db_session: AsyncSession) -> None:
    tenant_id, business_id_a = await _create_tenant_and_business(db_session)
    _, business_id_b = await _create_tenant_and_business(db_session)

    db_session.add(
        IntentPatternModel(
            tenant_id=tenant_id,
            business_id=business_id_a,
            intent=Intent.GREETING.value,
            pattern="yo",
        )
    )
    await db_session.flush()

    repository = PostgresIntentPatternRepository(db_session)
    patterns_for_b = await repository.get_patterns(tenant_id=tenant_id, business_id=business_id_b)

    assert "yo" not in patterns_for_b[Intent.GREETING]


async def test_custom_pattern_is_isolated_to_its_tenant(db_session: AsyncSession) -> None:
    tenant_id_a, business_id = await _create_tenant_and_business(db_session)
    tenant_id_b, _ = await _create_tenant_and_business(db_session)

    db_session.add(
        IntentPatternModel(
            tenant_id=tenant_id_a,
            business_id=business_id,
            intent=Intent.GREETING.value,
            pattern="yo",
        )
    )
    await db_session.flush()

    repository = PostgresIntentPatternRepository(db_session)
    patterns_for_b = await repository.get_patterns(tenant_id=tenant_id_b, business_id=business_id)

    assert "yo" not in patterns_for_b[Intent.GREETING]


async def test_add_pattern_then_get_patterns_includes_it(db_session: AsyncSession) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    repository = PostgresIntentPatternRepository(db_session)

    await repository.add_pattern(
        tenant_id=tenant_id, business_id=business_id, intent=Intent.GREETING, pattern="yo"
    )

    patterns = await repository.get_patterns(tenant_id=tenant_id, business_id=business_id)

    assert "yo" in patterns[Intent.GREETING]


async def test_add_pattern_twice_is_idempotent(db_session: AsyncSession) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    repository = PostgresIntentPatternRepository(db_session)

    await repository.add_pattern(
        tenant_id=tenant_id, business_id=business_id, intent=Intent.GREETING, pattern="yo"
    )
    await repository.add_pattern(
        tenant_id=tenant_id, business_id=business_id, intent=Intent.GREETING, pattern="yo"
    )

    custom = await repository.list_custom_patterns(tenant_id=tenant_id, business_id=business_id)

    assert custom == [(Intent.GREETING, "yo")]


async def test_list_custom_patterns_excludes_builtin_patterns(db_session: AsyncSession) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    repository = PostgresIntentPatternRepository(db_session)

    await repository.add_pattern(
        tenant_id=tenant_id, business_id=business_id, intent=Intent.GREETING, pattern="yo"
    )

    custom = await repository.list_custom_patterns(tenant_id=tenant_id, business_id=business_id)

    assert custom == [(Intent.GREETING, "yo")]
    assert "hi" not in [pattern for _, pattern in custom]


async def test_remove_pattern_deletes_it_and_returns_true(db_session: AsyncSession) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    repository = PostgresIntentPatternRepository(db_session)

    await repository.add_pattern(
        tenant_id=tenant_id, business_id=business_id, intent=Intent.GREETING, pattern="yo"
    )

    removed = await repository.remove_pattern(
        tenant_id=tenant_id, business_id=business_id, intent=Intent.GREETING, pattern="yo"
    )

    assert removed is True

    patterns = await repository.get_patterns(tenant_id=tenant_id, business_id=business_id)
    assert "yo" not in patterns[Intent.GREETING]


async def test_remove_pattern_returns_false_when_nothing_matched(
    db_session: AsyncSession,
) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    repository = PostgresIntentPatternRepository(db_session)

    removed = await repository.remove_pattern(
        tenant_id=tenant_id, business_id=business_id, intent=Intent.GREETING, pattern="never-added"
    )

    assert removed is False
