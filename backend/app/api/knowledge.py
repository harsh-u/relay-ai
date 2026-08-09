from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.app.api.schemas.knowledge import ClearKnowledgeCacheResponse
from backend.app.domain.knowledge.repository import AnsweredQuestionRepository
from backend.app.infrastructure.knowledge.dependencies import get_answered_question_repository

router = APIRouter(
    prefix="/v1",
    tags=["knowledge"],
)


@router.delete("/knowledge/cache", response_model=ClearKnowledgeCacheResponse)
async def clear_knowledge_cache(
    tenant_id: Annotated[
        str, Query(min_length=1, description="The tenant this business belongs to.")
    ],
    business_id: Annotated[
        str, Query(min_length=1, description="The business whose cache to clear.")
    ],
    answered_question_repository: Annotated[
        AnsweredQuestionRepository,
        Depends(get_answered_question_repository),
    ],
    agent_id: Annotated[
        str | None,
        Query(
            description=(
                "Only meaningful for businesses in 'isolated' scope. If "
                "given, only that agent's cache is cleared. If omitted, "
                "the ENTIRE business's cache is cleared - every agent, "
                "not 'no agent'. This is irreversible."
            ),
        ),
    ] = None,
) -> ClearKnowledgeCacheResponse:
    """Clear cached answers immediately, e.g. after a policy changes and you
    don't want to wait for the TTL to expire naturally.

    Warning: omitting agent_id clears every agent's cache for this
    business, not just an unscoped bucket. There is no undo."""

    deleted = await answered_question_repository.clear(
        tenant_id=tenant_id,
        business_id=business_id,
        agent_id=agent_id,
    )

    return ClearKnowledgeCacheResponse(deleted=deleted)
