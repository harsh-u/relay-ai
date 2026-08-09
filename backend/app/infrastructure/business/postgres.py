from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.business.knowledge_scope import KnowledgeScope
from backend.app.domain.business.repository import BusinessSettingsRepository
from backend.app.domain.business.settings import BusinessKnowledgeSettings
from backend.app.models.business import Business


class PostgresBusinessSettingsRepository(BusinessSettingsRepository):
    """Resolves a business's knowledge-cache configuration from the
    businesses table, falling back to the global default TTL when a
    business hasn't overridden it."""

    def __init__(self, session: AsyncSession, default_ttl_days: int) -> None:
        self._session = session
        self._default_ttl_days = default_ttl_days

    async def get_knowledge_settings(
        self,
        tenant_id: str,
        business_id: str,
    ) -> BusinessKnowledgeSettings:
        statement = select(Business).where(
            Business.id == UUID(business_id),
            Business.tenant_id == UUID(tenant_id),
        )

        result = await self._session.execute(statement)
        business = result.scalar_one_or_none()

        if business is None:
            return BusinessKnowledgeSettings(
                knowledge_scope=KnowledgeScope.SHARED,
                knowledge_ttl_days=self._default_ttl_days,
            )

        return BusinessKnowledgeSettings(
            knowledge_scope=KnowledgeScope(business.knowledge_scope),
            knowledge_ttl_days=business.knowledge_ttl_days or self._default_ttl_days,
        )

    async def update_knowledge_settings(
        self,
        tenant_id: str,
        business_id: str,
        knowledge_scope: KnowledgeScope | None,
        knowledge_ttl_days: int | None,
    ) -> BusinessKnowledgeSettings | None:
        statement = select(Business).where(
            Business.id == UUID(business_id),
            Business.tenant_id == UUID(tenant_id),
        )

        result = await self._session.execute(statement)
        business = result.scalar_one_or_none()

        if business is None:
            return None

        if knowledge_scope is not None:
            business.knowledge_scope = knowledge_scope.value

        if knowledge_ttl_days is not None:
            business.knowledge_ttl_days = knowledge_ttl_days

        await self._session.flush()

        return BusinessKnowledgeSettings(
            knowledge_scope=KnowledgeScope(business.knowledge_scope),
            knowledge_ttl_days=business.knowledge_ttl_days or self._default_ttl_days,
        )
