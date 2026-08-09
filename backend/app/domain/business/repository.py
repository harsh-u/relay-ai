from abc import ABC, abstractmethod

from backend.app.domain.business.settings import BusinessKnowledgeSettings


class BusinessSettingsRepository(ABC):
    """Resolves a business's knowledge-cache configuration."""

    @abstractmethod
    async def get_knowledge_settings(
        self,
        tenant_id: str,
        business_id: str,
    ) -> BusinessKnowledgeSettings:
        raise NotImplementedError
