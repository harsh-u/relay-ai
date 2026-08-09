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

    @abstractmethod
    async def add_pattern(
        self,
        tenant_id: str,
        business_id: str,
        intent: Intent,
        pattern: str,
    ) -> None:
        """Add a business-specific custom trigger phrase. Idempotent - adding
        the same (intent, pattern) twice for a business is a no-op."""
        raise NotImplementedError

    @abstractmethod
    async def remove_pattern(
        self,
        tenant_id: str,
        business_id: str,
        intent: Intent,
        pattern: str,
    ) -> bool:
        """Remove a business-specific custom trigger phrase. Returns True if
        a matching pattern existed and was removed, False otherwise. Never
        removes RelayAI's builtin defaults - only a business's own additions."""
        raise NotImplementedError

    @abstractmethod
    async def list_custom_patterns(
        self,
        tenant_id: str,
        business_id: str,
    ) -> list[tuple[Intent, str]]:
        """List only this business's own custom patterns (not the merged
        view with builtin defaults that get_patterns returns)."""
        raise NotImplementedError
