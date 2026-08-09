from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.business.knowledge_scope import KnowledgeScope
from backend.app.infrastructure.business.postgres import PostgresBusinessSettingsRepository
from backend.app.models.business import Business
from backend.app.models.tenant import Tenant


async def _create_tenant_and_business(
    session: AsyncSession,
    *,
    knowledge_scope: str = "shared",
    knowledge_ttl_days: int | None = None,
) -> tuple[str, str]:
    tenant = Tenant(name="Test Tenant", slug=f"test-tenant-{uuid4()}")
    session.add(tenant)
    await session.flush()

    business = Business(
        tenant_id=tenant.id,
        name="Test Business",
        slug=f"test-business-{uuid4()}",
        knowledge_scope=knowledge_scope,
        knowledge_ttl_days=knowledge_ttl_days,
    )
    session.add(business)
    await session.flush()

    return str(tenant.id), str(business.id)


async def test_defaults_to_shared_scope_with_no_override(db_session: AsyncSession) -> None:
    tenant_id, business_id = await _create_tenant_and_business(db_session)
    repository = PostgresBusinessSettingsRepository(db_session, default_ttl_days=30)

    settings = await repository.get_knowledge_settings(tenant_id, business_id)

    assert settings.knowledge_scope == KnowledgeScope.SHARED
    assert settings.knowledge_ttl_days == 30


async def test_reads_isolated_scope_and_ttl_override(db_session: AsyncSession) -> None:
    tenant_id, business_id = await _create_tenant_and_business(
        db_session, knowledge_scope="isolated", knowledge_ttl_days=7
    )
    repository = PostgresBusinessSettingsRepository(db_session, default_ttl_days=30)

    settings = await repository.get_knowledge_settings(tenant_id, business_id)

    assert settings.knowledge_scope == KnowledgeScope.ISOLATED
    assert settings.knowledge_ttl_days == 7


async def test_unknown_business_falls_back_to_shared_default(db_session: AsyncSession) -> None:
    tenant_id, _ = await _create_tenant_and_business(db_session)
    repository = PostgresBusinessSettingsRepository(db_session, default_ttl_days=30)

    settings = await repository.get_knowledge_settings(tenant_id, str(uuid4()))

    assert settings.knowledge_scope == KnowledgeScope.SHARED
    assert settings.knowledge_ttl_days == 30
