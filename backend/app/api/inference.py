from typing import Annotated

from fastapi import APIRouter, Depends, Path

from backend.app.api.schemas.conversation import (
    AssistantMessageRequest,
    AssistantMessageResponse,
)
from backend.app.api.schemas.inference import (
    InferenceRequestBody,
    InferenceResponseBody,
)
from backend.app.application.conversation import ConversationService
from backend.app.application.inference import InferenceService
from backend.app.config.settings import get_settings
from backend.app.domain.analytics.repository import DecisionRepository
from backend.app.domain.business.repository import BusinessSettingsRepository
from backend.app.domain.conversation.store import ConversationStore
from backend.app.domain.embedding.provider import EmbeddingProvider
from backend.app.domain.inference import InferenceRequest
from backend.app.domain.knowledge.repository import AnsweredQuestionRepository
from backend.app.domain.matching.pattern_repository import IntentPatternRepository
from backend.app.infrastructure.analytics.dependencies import get_decision_repository
from backend.app.infrastructure.business.dependencies import get_business_settings_repository
from backend.app.infrastructure.conversation.dependencies import (
    get_conversation_store,
)
from backend.app.infrastructure.embedding.dependencies import get_embedding_provider
from backend.app.infrastructure.knowledge.dependencies import (
    get_answered_question_repository,
)
from backend.app.infrastructure.matching.dependencies import (
    get_intent_pattern_repository,
)

router = APIRouter(
    prefix="/v1",
    tags=["inference"],
)


@router.post("/inference", response_model=InferenceResponseBody)
async def inference(
    request: InferenceRequestBody,
    conversation_store: Annotated[
        ConversationStore,
        Depends(get_conversation_store),
    ],
    pattern_repository: Annotated[
        IntentPatternRepository,
        Depends(get_intent_pattern_repository),
    ],
    embedding_provider: Annotated[
        EmbeddingProvider,
        Depends(get_embedding_provider),
    ],
    answered_question_repository: Annotated[
        AnsweredQuestionRepository,
        Depends(get_answered_question_repository),
    ],
    business_settings_repository: Annotated[
        BusinessSettingsRepository,
        Depends(get_business_settings_repository),
    ],
    decision_repository: Annotated[
        DecisionRepository,
        Depends(get_decision_repository),
    ],
) -> InferenceResponseBody:
    """Process one STT-transcribed turn. Returns 'respond' with text to
    speak directly (skip your LLM), or 'fallback' meaning RelayAI has no
    answer - call your own LLM as usual, then report its answer back via
    POST /v1/conversations/{conversation_id}/messages."""

    inference_service = InferenceService(
        pattern_repository=pattern_repository,
        conversation_store=conversation_store,
        embedding_provider=embedding_provider,
        answered_question_repository=answered_question_repository,
        business_settings_repository=business_settings_repository,
        decision_repository=decision_repository,
        semantic_match_threshold=get_settings().embedding_similarity_threshold,
    )

    result = await inference_service.process(
        InferenceRequest(
            tenant_id=request.tenant_id,
            business_id=request.business_id,
            conversation_id=request.conversation_id,
            agent_id=request.agent_id,
            text=request.text,
        )
    )

    return InferenceResponseBody(
        action=result.action,
        text=result.text,
        source=result.source,
        intent=result.intent,
        similarity=result.similarity,
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=AssistantMessageResponse,
)
async def record_assistant_message(
    conversation_id: Annotated[
        str,
        Path(description="The same conversation_id used in this call's /v1/inference requests."),
    ],
    request: AssistantMessageRequest,
    conversation_store: Annotated[
        ConversationStore,
        Depends(get_conversation_store),
    ],
    embedding_provider: Annotated[
        EmbeddingProvider,
        Depends(get_embedding_provider),
    ],
    answered_question_repository: Annotated[
        AnsweredQuestionRepository,
        Depends(get_answered_question_repository),
    ],
) -> AssistantMessageResponse:
    """Report back what your LLM answered for a 'fallback' turn. This is
    also what feeds RelayAI's semantic knowledge cache - the question this
    answer responds to (the last thing the caller said in this
    conversation) gets cached so future callers asking something similar
    can be answered directly next time."""

    conversation_service = ConversationService(
        conversation_store=conversation_store,
        embedding_provider=embedding_provider,
        answered_question_repository=answered_question_repository,
        dedup_similarity_threshold=get_settings().embedding_similarity_threshold,
    )

    await conversation_service.record_assistant_response(
        tenant_id=request.tenant_id,
        business_id=request.business_id,
        conversation_id=conversation_id,
        agent_id=request.agent_id,
        text=request.text,
    )

    return AssistantMessageResponse(
        conversation_id=conversation_id,
        stored=True,
    )
