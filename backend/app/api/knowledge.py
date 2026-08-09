from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.api.schemas.knowledge import (
    AddAnsweredQuestionRequest,
    AddAnsweredQuestionResponse,
    AnsweredQuestionItem,
    ClearKnowledgeCacheResponse,
    ListAnsweredQuestionsResponse,
    UpdateKnowledgeSettingsRequest,
    UpdateKnowledgeSettingsResponse,
)
from backend.app.application.knowledge import KnowledgeService
from backend.app.config.settings import get_settings
from backend.app.domain.business.repository import BusinessSettingsRepository
from backend.app.domain.embedding.provider import EmbeddingProvider
from backend.app.domain.knowledge.repository import AnsweredQuestionRepository
from backend.app.infrastructure.business.dependencies import get_business_settings_repository
from backend.app.infrastructure.embedding.dependencies import get_embedding_provider
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


@router.get("/knowledge/settings", response_model=UpdateKnowledgeSettingsResponse)
async def get_knowledge_settings(
    tenant_id: Annotated[
        str, Query(min_length=1, description="The tenant this business belongs to.")
    ],
    business_id: Annotated[str, Query(min_length=1, description="The business to look up.")],
    business_settings_repository: Annotated[
        BusinessSettingsRepository,
        Depends(get_business_settings_repository),
    ],
) -> UpdateKnowledgeSettingsResponse:
    """Read a business's current knowledge-cache configuration, without
    changing it."""

    settings = await business_settings_repository.get_knowledge_settings(
        tenant_id=tenant_id,
        business_id=business_id,
    )

    return UpdateKnowledgeSettingsResponse(
        knowledge_scope=settings.knowledge_scope,
        knowledge_ttl_days=settings.knowledge_ttl_days,
    )


@router.patch("/knowledge/settings", response_model=UpdateKnowledgeSettingsResponse)
async def update_knowledge_settings(
    request: UpdateKnowledgeSettingsRequest,
    business_settings_repository: Annotated[
        BusinessSettingsRepository,
        Depends(get_business_settings_repository),
    ],
) -> UpdateKnowledgeSettingsResponse:
    """Configure how a business's knowledge cache behaves - whether its
    agents share one cache or stay isolated, and how long a cached answer
    stays eligible for reuse before it's treated as stale.

    This is the API alternative to updating the businesses table directly."""

    updated = await business_settings_repository.update_knowledge_settings(
        tenant_id=request.tenant_id,
        business_id=request.business_id,
        knowledge_scope=request.knowledge_scope,
        knowledge_ttl_days=request.knowledge_ttl_days,
    )

    if updated is None:
        raise HTTPException(status_code=404, detail="No such business for this tenant.")

    return UpdateKnowledgeSettingsResponse(
        knowledge_scope=updated.knowledge_scope,
        knowledge_ttl_days=updated.knowledge_ttl_days,
    )


@router.post("/knowledge/answers", response_model=AddAnsweredQuestionResponse)
async def add_answered_question(
    request: AddAnsweredQuestionRequest,
    embedding_provider: Annotated[
        EmbeddingProvider,
        Depends(get_embedding_provider),
    ],
    answered_question_repository: Annotated[
        AnsweredQuestionRepository,
        Depends(get_answered_question_repository),
    ],
) -> AddAnsweredQuestionResponse:
    """Seed the knowledge cache directly with a known (question, answer)
    pair, so it's reusable immediately - without waiting for a real caller
    to trigger a fallback and someone to report the answer back first."""

    knowledge_service = KnowledgeService(
        embedding_provider=embedding_provider,
        answered_question_repository=answered_question_repository,
        dedup_similarity_threshold=get_settings().embedding_similarity_threshold,
    )

    await knowledge_service.add_answered_question(
        tenant_id=request.tenant_id,
        business_id=request.business_id,
        agent_id=request.agent_id,
        question=request.question,
        answer=request.answer,
    )

    return AddAnsweredQuestionResponse(stored=True)


@router.get("/knowledge/answers", response_model=ListAnsweredQuestionsResponse)
async def list_answered_questions(
    tenant_id: Annotated[
        str, Query(min_length=1, description="The tenant this business belongs to.")
    ],
    business_id: Annotated[str, Query(min_length=1, description="The business to look up.")],
    answered_question_repository: Annotated[
        AnsweredQuestionRepository,
        Depends(get_answered_question_repository),
    ],
    agent_id: Annotated[
        str | None,
        Query(
            description=(
                "Only meaningful for businesses in 'isolated' scope. If "
                "given, only that agent's cached answers are listed."
            ),
        ),
    ] = None,
) -> ListAnsweredQuestionsResponse:
    """List a business's cached answers, newest first - for inspecting the
    knowledge cache (e.g. to see dedup and TTL actually working), not for
    matching. Capped at 200 rows."""

    answers = await answered_question_repository.list_all(
        tenant_id=tenant_id,
        business_id=business_id,
        agent_id=agent_id,
    )

    return ListAnsweredQuestionsResponse(
        answers=[
            AnsweredQuestionItem(
                agent_id=answer.agent_id,
                question=answer.question,
                answer=answer.answer,
                created_at=answer.created_at,
            )
            for answer in answers
        ]
    )
