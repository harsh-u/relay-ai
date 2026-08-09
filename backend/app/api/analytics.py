from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.app.api.schemas.analytics import DecisionSummaryResponse
from backend.app.domain.analytics.repository import DecisionRepository
from backend.app.infrastructure.analytics.dependencies import get_decision_repository

router = APIRouter(
    prefix="/v1",
    tags=["analytics"],
)


@router.get("/analytics/summary", response_model=DecisionSummaryResponse)
async def get_decision_summary(
    tenant_id: Annotated[
        str, Query(min_length=1, description="The tenant this business belongs to.")
    ],
    business_id: Annotated[str, Query(min_length=1, description="The business to summarize.")],
    decision_repository: Annotated[
        DecisionRepository,
        Depends(get_decision_repository),
    ],
) -> DecisionSummaryResponse:
    """Summarize how often RelayAI avoided the LLM for a business, and via
    which mechanism (builtin rule, conversation recall, or knowledge cache)."""

    summary = await decision_repository.summarize(tenant_id=tenant_id, business_id=business_id)

    return DecisionSummaryResponse(
        total=summary.total,
        respond_count=summary.respond_count,
        fallback_count=summary.fallback_count,
        avoided_llm_rate=summary.avoided_llm_rate,
        respond_by_source=summary.respond_by_source,
    )
