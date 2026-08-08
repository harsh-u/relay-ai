from abc import ABC, abstractmethod

from backend.app.domain.matching.intent import Intent


class IntentPatternRepository(ABC):
    """Resolves the effective intent trigger phrases for a business.

    Implementations must include RelayAI's builtin defaults alongside any
    business-specific custom phrases, so callers never need to merge the two.
    """

    @abstractmethod
    async def get_patterns(
        self,
        tenant_id: str,
        business_id: str,
    ) -> dict[Intent, tuple[str, ...]]:
        raise NotImplementedError
