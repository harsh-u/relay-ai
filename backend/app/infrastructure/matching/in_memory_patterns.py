from backend.app.domain.matching.builtin_patterns import BUILTIN_PATTERNS
from backend.app.domain.matching.intent import Intent
from backend.app.domain.matching.pattern_repository import IntentPatternRepository


class InMemoryIntentPatternRepository(IntentPatternRepository):
    """In-memory pattern repository, for tests and local development.

    Custom patterns are added on top of the builtin defaults, keyed by
    (tenant_id, business_id).
    """

    def __init__(self) -> None:
        self._custom_patterns: dict[tuple[str, str], dict[Intent, list[str]]] = {}

    def add_custom_pattern(
        self,
        tenant_id: str,
        business_id: str,
        intent: Intent,
        pattern: str,
    ) -> None:
        scoped = self._custom_patterns.setdefault((tenant_id, business_id), {})
        scoped.setdefault(intent, []).append(pattern)

    async def get_patterns(
        self,
        tenant_id: str,
        business_id: str,
    ) -> dict[Intent, tuple[str, ...]]:
        custom = self._custom_patterns.get((tenant_id, business_id), {})

        merged: dict[Intent, tuple[str, ...]] = {}

        for intent in Intent:
            patterns = list(BUILTIN_PATTERNS.get(intent, ())) + custom.get(intent, [])
            merged[intent] = tuple(patterns)

        return merged
