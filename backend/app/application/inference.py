from backend.app.domain.conversation.state import ConversationState
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

        state = await self._conversation_store.get(
            request.conversation_id,
        )

        if state is None:
            state = ConversationState(
                conversation_id=request.conversation_id,
            )

        if not request.text.strip():
            return InferenceResponse(
                action=InferenceAction.FALLBACK,
            )

        intent = await self._intent_matcher.match(request.text)

        if intent == Intent.GREETING:
            response_text = "Hello! How can I help you?"

            await self._save_state(
                state=state,
                user_message=request.text,
                assistant_response=response_text,
            )

            return InferenceResponse(
                action=InferenceAction.RESPOND,
                text=response_text,
                source="builtin:greeting",
                intent=intent,
            )

        if intent == Intent.REPEAT_REQUEST:
            if state.last_assistant_response:
                response_text = state.last_assistant_response

                await self._save_state(
                    state=state,
                    user_message=request.text,
                    assistant_response=response_text,
                )

                return InferenceResponse(
                    action=InferenceAction.RESPOND,
                    text=response_text,
                    source="conversation:last_response",
                    intent=intent,
                )

            return InferenceResponse(
                action=InferenceAction.FALLBACK,
                intent=intent,
            )

        await self._save_state(
            state=state,
            user_message=request.text,
            assistant_response=None,
        )

        return InferenceResponse(
            action=InferenceAction.FALLBACK,
        )

    async def _save_state(
        self,
        state: ConversationState,
        user_message: str,
        assistant_response: str | None,
    ) -> None:
        """Update and persist the minimal conversation state."""

        state.last_user_message = user_message

        if assistant_response is not None:
            state.last_assistant_response = assistant_response

        await self._conversation_store.save(state)
