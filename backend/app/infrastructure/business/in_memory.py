from backend.app.domain.business.knowledge_scope import KnowledgeScope
from backend.app.domain.business.repository import BusinessSettingsRepository
from backend.app.domain.business.settings import BusinessKnowledgeSettings


class InMemoryBusinessSettingsRepository(BusinessSettingsRepository):
    """In-memory business settings, for tests. Defaults every business to
    shared scope with a generous TTL unless a test overrides it."""

    def __init__(self, default_ttl_days: int = 30) -> None:
        self._default_ttl_days = default_ttl_days
        self._overrides: dict[tuple[str, str], BusinessKnowledgeSettings] = {}

    def set_knowledge_settings(
        self,
        tenant_id: str,
        business_id: str,
        settings: BusinessKnowledgeSettings,
    ) -> None:
        self._overrides[(tenant_id, business_id)] = settings

    async def get_knowledge_settings(
        self,
        tenant_id: str,
        business_id: str,
    ) -> BusinessKnowledgeSettings:
        return self._overrides.get(
            (tenant_id, business_id),
            BusinessKnowledgeSettings(
                knowledge_scope=KnowledgeScope.SHARED,
                knowledge_ttl_days=self._default_ttl_days,
            ),
        )
