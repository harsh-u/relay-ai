from backend.app.domain.inference import (
    InferenceAction,
    InferenceRequest,
    InferenceResponse,
)
from backend.app.domain.matching.intent import Intent
from backend.app.infrastructure.matching.rule_based import RuleBasedIntentMatcher


class InferenceService:
    """Core RelayAI inference decision service."""

    def __init__(self, intent_matcher: RuleBasedIntentMatcher) -> None:
        self._intent_matcher = intent_matcher

    async def process(
        self,
        request: InferenceRequest,
    ) -> InferenceResponse:
        """Process an inference request."""

        if not request.text.strip():
            return InferenceResponse(
                action=InferenceAction.FALLBACK,
            )

        intent = await self._intent_matcher.match(request.text)

        if intent == Intent.GREETING:
            return InferenceResponse(
                action=InferenceAction.RESPOND,
                text="Hello! How can I help you?",
                source="builtin:greeting",
                intent=intent,
            )

        if intent == Intent.REPEAT_REQUEST:
            return InferenceResponse(
                action=InferenceAction.FALLBACK,
                intent=intent,
            )

        return InferenceResponse(
            action=InferenceAction.FALLBACK,
        )
