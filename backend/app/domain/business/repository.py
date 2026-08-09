from abc import ABC, abstractmethod

from backend.app.domain.business.knowledge_scope import KnowledgeScope
from backend.app.domain.business.settings import BusinessKnowledgeSettings


class BusinessSettingsRepository(ABC):
    """Resolves and updates a business's knowledge-cache configuration."""

    @abstractmethod
    async def get_knowledge_settings(
        self,
        tenant_id: str,
        business_id: str,
    ) -> BusinessKnowledgeSettings:
        raise NotImplementedError

    @abstractmethod
    async def update_knowledge_settings(
        self,
        tenant_id: str,
        business_id: str,
        knowledge_scope: KnowledgeScope | None,
        knowledge_ttl_days: int | None,
    ) -> BusinessKnowledgeSettings | None:
        """Update only the fields given (None means leave unchanged).

        Returns the resulting settings, or None if no such business exists
        for this tenant.
        """
        raise NotImplementedError
