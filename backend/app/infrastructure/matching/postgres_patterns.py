from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.matching.builtin_patterns import BUILTIN_PATTERNS
from backend.app.domain.matching.intent import Intent
from backend.app.domain.matching.pattern_repository import IntentPatternRepository
from backend.app.models.intent_pattern import IntentPatternModel


class PostgresIntentPatternRepository(IntentPatternRepository):
    """PostgreSQL-backed pattern repository.

    Merges each business's custom phrases on top of RelayAI's builtin
    defaults, per intent.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_patterns(
        self,
        tenant_id: str,
        business_id: str,
    ) -> dict[Intent, tuple[str, ...]]:
        statement = select(IntentPatternModel).where(
            IntentPatternModel.tenant_id == UUID(tenant_id),
            IntentPatternModel.business_id == UUID(business_id),
        )

        result = await self._session.execute(statement)
        rows = result.scalars().all()

        custom: dict[Intent, list[str]] = {}

        for row in rows:
            custom.setdefault(Intent(row.intent), []).append(row.pattern)

        merged: dict[Intent, tuple[str, ...]] = {}

        for intent in Intent:
            patterns = list(BUILTIN_PATTERNS.get(intent, ())) + custom.get(intent, [])
            merged[intent] = tuple(patterns)

        return merged
