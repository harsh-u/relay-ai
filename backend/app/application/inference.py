from backend.app.domain.inference import (
    InferenceAction,
    InferenceRequest,
    InferenceResponse,
)


class InferenceService:
    """Core RelayAI inference decision service."""

    async def process(
        self,
        request: InferenceRequest,
    ) -> InferenceResponse:
        """Process an inference request."""

        text = request.text.strip()

        if not text:
            return InferenceResponse(
                action=InferenceAction.FALLBACK,
            )

        normalized_text = text.lower()

        greetings = {
            "hi",
            "hello",
            "hey",
            "hi there",
            "hello there",
            "hey there",
        }

        if normalized_text in greetings:
            return InferenceResponse(
                action=InferenceAction.RESPOND,
                text="Hello! How can I help you?",
                source="builtin:greeting",
            )

        return InferenceResponse(
            action=InferenceAction.FALLBACK,
        )
