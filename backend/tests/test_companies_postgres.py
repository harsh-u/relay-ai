from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.business.knowledge_scope import KnowledgeScope
from backend.app.infrastructure.business.postgres_company import PostgresCompanyRepository


async def test_create_persists_a_tenant_and_business_pair(db_session: AsyncSession) -> None:
    repository = PostgresCompanyRepository(db_session, default_ttl_days=30)

    company = await repository.create(name="Bright Smile Dental")

    assert UUID(company.id)
    assert UUID(company.tenant_id)
    assert company.id != company.tenant_id
    assert company.name == "Bright Smile Dental"
    assert company.knowledge_scope == KnowledgeScope.SHARED
    assert company.knowledge_ttl_days == 30


async def test_list_all_returns_created_companies_newest_first(db_session: AsyncSession) -> None:
    repository = PostgresCompanyRepository(db_session, default_ttl_days=30)

    first = await repository.create(name="First Company")
    second = await repository.create(name="Second Company")

    companies = await repository.list_all()

    ids = [company.id for company in companies]
    assert ids.index(second.id) < ids.index(first.id)
