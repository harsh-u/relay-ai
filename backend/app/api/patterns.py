from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.app.api.schemas.patterns import (
    AddPatternRequest,
    AddPatternResponse,
    ListPatternsResponse,
    PatternItem,
    RemovePatternResponse,
)
from backend.app.domain.matching.intent import Intent
from backend.app.domain.matching.pattern_repository import IntentPatternRepository
from backend.app.infrastructure.matching.dependencies import get_intent_pattern_repository

router = APIRouter(
    prefix="/v1",
    tags=["patterns"],
)


@router.post("/patterns", response_model=AddPatternResponse)
async def add_pattern(
    request: AddPatternRequest,
    pattern_repository: Annotated[
        IntentPatternRepository,
        Depends(get_intent_pattern_repository),
    ],
) -> AddPatternResponse:
    """Add a business-specific custom trigger phrase, so a business can
    self-manage this instead of requiring a direct database insert."""

    await pattern_repository.add_pattern(
        tenant_id=request.tenant_id,
        business_id=request.business_id,
        intent=request.intent,
        pattern=request.pattern,
    )

    return AddPatternResponse(stored=True)


@router.get("/patterns", response_model=ListPatternsResponse)
async def list_patterns(
    tenant_id: Annotated[str, Query(min_length=1, description="The tenant to look up.")],
    business_id: Annotated[str, Query(min_length=1, description="The business to look up.")],
    pattern_repository: Annotated[
        IntentPatternRepository,
        Depends(get_intent_pattern_repository),
    ],
) -> ListPatternsResponse:
    """List a business's own custom patterns (not RelayAI's builtin defaults
    that already apply to every business regardless)."""

    patterns = await pattern_repository.list_custom_patterns(
        tenant_id=tenant_id,
        business_id=business_id,
    )

    return ListPatternsResponse(
        patterns=[PatternItem(intent=intent, pattern=pattern) for intent, pattern in patterns]
    )


@router.delete("/patterns", response_model=RemovePatternResponse)
async def remove_pattern(
    tenant_id: Annotated[
        str, Query(min_length=1, description="The tenant this business belongs to.")
    ],
    business_id: Annotated[
        str, Query(min_length=1, description="The business to remove the pattern from.")
    ],
    intent: Annotated[Intent, Query(description="Which intent the pattern was added under.")],
    pattern: Annotated[str, Query(min_length=1, description="The exact phrase to remove.")],
    pattern_repository: Annotated[
        IntentPatternRepository,
        Depends(get_intent_pattern_repository),
    ],
) -> RemovePatternResponse:
    """Remove a business-specific custom trigger phrase. RelayAI's builtin
    patterns are never affected by this - only a business's own additions."""

    removed = await pattern_repository.remove_pattern(
        tenant_id=tenant_id,
        business_id=business_id,
        intent=intent,
        pattern=pattern,
    )

    return RemovePatternResponse(removed=removed)
