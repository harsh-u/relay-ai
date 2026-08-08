from typing import Annotated

from fastapi import APIRouter, Depends

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
from backend.app.domain.conversation.store import ConversationStore
from backend.app.domain.inference import InferenceRequest
from backend.app.domain.matching.pattern_repository import IntentPatternRepository
from backend.app.infrastructure.conversation.dependencies import (
    get_conversation_store,
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
) -> InferenceResponseBody:
    """Process an STT request through the RelayAI inference layer."""

    inference_service = InferenceService(
        pattern_repository=pattern_repository,
        conversation_store=conversation_store,
    )

    result = await inference_service.process(
        InferenceRequest(
            tenant_id=request.tenant_id,
            business_id=request.business_id,
            conversation_id=request.conversation_id,
            text=request.text,
        )
    )

    return InferenceResponseBody(
        action=result.action,
        text=result.text,
        source=result.source,
        intent=result.intent,
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=AssistantMessageResponse,
)
async def record_assistant_message(
    conversation_id: str,
    request: AssistantMessageRequest,
    conversation_store: Annotated[
        ConversationStore,
        Depends(get_conversation_store),
    ],
) -> AssistantMessageResponse:
    """Store an assistant response in conversation history."""

    conversation_service = ConversationService(
        conversation_store=conversation_store,
    )

    await conversation_service.record_assistant_response(
        tenant_id=request.tenant_id,
        business_id=request.business_id,
        conversation_id=conversation_id,
        text=request.text,
    )

    return AssistantMessageResponse(
        conversation_id=conversation_id,
        stored=True,
    )
