from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.app.api.schemas.conversation import (
    AssistantMessageRequest,
    AssistantMessageResponse,
    ConversationHistoryResponse,
    ConversationTurnResponse,
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
from backend.app.domain.conversation.scope import ConversationScope
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
        matched_question=result.matched_question,
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
    pattern_repository: Annotated[
        IntentPatternRepository,
        Depends(get_intent_pattern_repository),
    ],
) -> AssistantMessageResponse:
    """Report back what your LLM answered for a 'fallback' turn. This is
    also what feeds RelayAI's semantic knowledge cache - the question this
    answer responds to (the last thing the caller said in this
    conversation) gets cached so future callers asking something similar
    can be answered directly next time. Not cached if that question was
    itself a recognized intent (e.g. "repeat that" with no prior context) -
    only genuinely unanswered business questions get cached."""

    conversation_service = ConversationService(
        conversation_store=conversation_store,
        embedding_provider=embedding_provider,
        answered_question_repository=answered_question_repository,
        pattern_repository=pattern_repository,
        dedup_similarity_threshold=get_settings().embedding_similarity_threshold,
    )

    cached = await conversation_service.record_assistant_response(
        tenant_id=request.tenant_id,
        business_id=request.business_id,
        conversation_id=conversation_id,
        agent_id=request.agent_id,
        text=request.text,
    )

    return AssistantMessageResponse(
        conversation_id=conversation_id,
        stored=True,
        cached=cached,
    )


@router.get(
    "/conversations/{conversation_id}/history",
    response_model=ConversationHistoryResponse,
)
async def get_conversation_history(
    conversation_id: Annotated[str, Path(description="The conversation to review.")],
    tenant_id: Annotated[
        str, Query(min_length=1, description="The tenant this business belongs to.")
    ],
    business_id: Annotated[
        str, Query(min_length=1, description="The business this call belongs to.")
    ],
    conversation_store: Annotated[
        ConversationStore,
        Depends(get_conversation_store),
    ],
    decision_repository: Annotated[
        DecisionRepository,
        Depends(get_decision_repository),
    ],
) -> ConversationHistoryResponse:
    """Review a conversation after the fact: the full transcript, with each
    user turn annotated with how RelayAI decided to answer it (action,
    source, similarity, and which cached question it was judged against) -
    for seeing why an answer came out the way it did without needing to
    watch it happen live or query the database directly."""

    scope = ConversationScope(
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id=conversation_id,
    )
    messages = await conversation_store.get_recent_messages(scope=scope, limit=200)
    decisions = await decision_repository.list_for_conversation(
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id=conversation_id,
    )
    decision_iterator = iter(decisions)

    turns = []
    for message in messages:
        decision = next(decision_iterator, None) if message.role == "user" else None

        turns.append(
            ConversationTurnResponse(
                role=message.role,
                text=message.text,
                created_at=message.created_at,
                action=decision.action.value if decision else None,
                source=decision.source if decision else None,
                intent=decision.intent if decision else None,
                similarity=decision.similarity if decision else None,
                matched_question=decision.matched_question if decision else None,
            )
        )

    return ConversationHistoryResponse(conversation_id=conversation_id, turns=turns)
