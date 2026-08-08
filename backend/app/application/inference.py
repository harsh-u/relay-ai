from backend.app.domain.conversation.scope import ConversationScope
from backend.app.domain.conversation.store import ConversationStore
from backend.app.domain.inference import (
    InferenceAction,
    InferenceRequest,
    InferenceResponse,
)
from backend.app.domain.matching.intent import Intent
from backend.app.infrastructure.matching.rule_based import RuleBasedIntentMatcher


class InferenceService:
    """Core RelayAI inference decision service."""

    def __init__(
        self,
        intent_matcher: RuleBasedIntentMatcher,
        conversation_store: ConversationStore,
    ) -> None:
        self._intent_matcher = intent_matcher
        self._conversation_store = conversation_store

    async def process(
        self,
        request: InferenceRequest,
    ) -> InferenceResponse:
        """Process an inference request."""

        scope = ConversationScope(
            tenant_id=request.tenant_id,
            business_id=request.business_id,
            conversation_id=request.conversation_id,
        )

        if not request.text.strip():
            return InferenceResponse(
                action=InferenceAction.FALLBACK,
            )

        intent = await self._intent_matcher.match(request.text)

        if intent == Intent.GREETING:
            response_text = "Hello! How can I help you?"

            await self._conversation_store.save_assistant_response(
                scope=scope,
                text=response_text,
            )

            return InferenceResponse(
                action=InferenceAction.RESPOND,
                text=response_text,
                source="builtin:greeting",
                intent=intent,
            )

        if intent == Intent.REPEAT_REQUEST:
            last_response = await self._conversation_store.get_last_assistant_response(
                scope=scope,
            )

            if last_response is not None:
                return InferenceResponse(
                    action=InferenceAction.RESPOND,
                    text=last_response.text,
                    source="conversation:last_response",
                    intent=intent,
                )

            return InferenceResponse(
                action=InferenceAction.FALLBACK,
                intent=intent,
            )

        return InferenceResponse(
            action=InferenceAction.FALLBACK,
        )
