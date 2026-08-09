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
    tenant_id: Annotated[str, Query(min_length=1)],
    business_id: Annotated[str, Query(min_length=1)],
    answered_question_repository: Annotated[
        AnsweredQuestionRepository,
        Depends(get_answered_question_repository),
    ],
    agent_id: Annotated[str | None, Query()] = None,
) -> ClearKnowledgeCacheResponse:
    """Clear cached answers for a business, e.g. after a policy changes and
    you don't want to wait for the TTL. Pass agent_id to clear only that
    agent's own cache (only meaningful for businesses in isolated mode)."""

    deleted = await answered_question_repository.clear(
        tenant_id=tenant_id,
        business_id=business_id,
        agent_id=agent_id,
    )

    return ClearKnowledgeCacheResponse(deleted=deleted)
