from datetime import UTC, datetime
from uuid import uuid4

from backend.app.domain.business.company import Company, slugify
from backend.app.domain.business.company_repository import CompanyRepository
from backend.app.domain.business.knowledge_scope import KnowledgeScope


class InMemoryCompanyRepository(CompanyRepository):
    def __init__(self, default_ttl_days: int = 30) -> None:
        self._default_ttl_days = default_ttl_days
        self._companies: list[Company] = []

    async def create(self, name: str) -> Company:
        company = Company(
            id=str(uuid4()),
            tenant_id=str(uuid4()),
            name=name,
            slug=f"{slugify(name)}-{uuid4().hex[:6]}",
            knowledge_scope=KnowledgeScope.SHARED,
            knowledge_ttl_days=self._default_ttl_days,
            created_at=datetime.now(UTC),
        )
        self._companies.append(company)
        return company

    async def list_all(self) -> list[Company]:
        return sorted(self._companies, key=lambda company: company.created_at, reverse=True)

    async def delete(self, business_id: str) -> bool:
        for index, company in enumerate(self._companies):
            if company.id == business_id:
                del self._companies[index]
                return True

        return False
