from fastapi import APIRouter

from backend.app.api.schemas.inference import (
    InferenceRequestBody,
    InferenceResponseBody,
)
from backend.app.application.inference import InferenceService
from backend.app.domain.inference import InferenceRequest
from backend.app.infrastructure.matching.rule_based import RuleBasedIntentMatcher

router = APIRouter(
    prefix="/v1",
    tags=["inference"],
)

inference_service = InferenceService(
    intent_matcher=RuleBasedIntentMatcher(),
)


@router.post("/inference", response_model=InferenceResponseBody)
async def inference(
    request: InferenceRequestBody,
) -> InferenceResponseBody:
    """Process an STT request through the RelayAI inference layer."""

    result = await inference_service.process(
        InferenceRequest(
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
