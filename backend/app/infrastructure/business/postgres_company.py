from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.business.company import Company, slugify
from backend.app.domain.business.company_repository import CompanyRepository
from backend.app.domain.business.knowledge_scope import KnowledgeScope
from backend.app.models.business import Business
from backend.app.models.tenant import Tenant


class PostgresCompanyRepository(CompanyRepository):
    """Creates a Tenant + Business pair for every company, and lists every
    Business row as a company - a business created directly (outside this
    repository) shows up too, under its own tenant."""

    def __init__(self, session: AsyncSession, default_ttl_days: int) -> None:
        self._session = session
        self._default_ttl_days = default_ttl_days

    async def create(self, name: str) -> Company:
        slug = f"{slugify(name)}-{uuid4().hex[:6]}"

        tenant = Tenant(name=name, slug=slug)
        self._session.add(tenant)
        await self._session.flush()

        business = Business(tenant_id=tenant.id, name=name, slug=slug)
        self._session.add(business)
        await self._session.flush()

        return self._to_company(business)

    async def list_all(self) -> list[Company]:
        statement = select(Business).order_by(Business.created_at.desc())
        result = await self._session.execute(statement)

        return [self._to_company(business) for business in result.scalars()]

    def _to_company(self, business: Business) -> Company:
        return Company(
            id=str(business.id),
            tenant_id=str(business.tenant_id),
            name=business.name,
            slug=business.slug,
            knowledge_scope=KnowledgeScope(business.knowledge_scope),
            knowledge_ttl_days=business.knowledge_ttl_days or self._default_ttl_days,
            created_at=business.created_at,
        )
