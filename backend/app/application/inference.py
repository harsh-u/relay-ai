from backend.app.domain.conversation.qa_pairs import extract_answered_questions
from backend.app.domain.conversation.scope import ConversationScope
from backend.app.domain.conversation.store import ConversationStore
from backend.app.domain.embedding.provider import EmbeddingProvider
from backend.app.domain.embedding.similarity import cosine_similarity
from backend.app.domain.inference import (
    InferenceAction,
    InferenceRequest,
    InferenceResponse,
)
from backend.app.domain.matching.intent import Intent
from backend.app.domain.matching.pattern_repository import IntentPatternRepository
from backend.app.infrastructure.matching.rule_based import RuleBasedIntentMatcher


class InferenceService:
    """Core RelayAI inference decision service."""

    def __init__(
        self,
        pattern_repository: IntentPatternRepository,
        conversation_store: ConversationStore,
        embedding_provider: EmbeddingProvider,
        semantic_match_threshold: float,
    ) -> None:
        self._pattern_repository = pattern_repository
        self._conversation_store = conversation_store
        self._embedding_provider = embedding_provider
        self._semantic_match_threshold = semantic_match_threshold

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

        await self._conversation_store.save_user_message(
            scope=scope,
            text=request.text,
        )

        patterns = await self._pattern_repository.get_patterns(
            tenant_id=request.tenant_id,
            business_id=request.business_id,
        )
        intent_matcher = RuleBasedIntentMatcher(patterns=patterns)
        intent = await intent_matcher.match(request.text)

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

        return await self._match_answered_question(scope, request.text)

    async def _match_answered_question(
        self,
        scope: ConversationScope,
        text: str,
    ) -> InferenceResponse:
        """Reuse an earlier answer if this question means the same as one
        already asked and answered in this conversation, even if worded
        differently."""

        history = await self._conversation_store.get_recent_messages(scope=scope)
        qa_pairs = extract_answered_questions(history)

        if not qa_pairs:
            return InferenceResponse(action=InferenceAction.FALLBACK)

        past_questions = [question for question, _ in qa_pairs]
        vectors = await self._embedding_provider.embed([text, *past_questions])
        query_vector, past_vectors = vectors[0], vectors[1:]

        best_index: int | None = None
        best_similarity = 0.0

        for index, past_vector in enumerate(past_vectors):
            similarity = cosine_similarity(query_vector, past_vector)

            if similarity > best_similarity:
                best_similarity = similarity
                best_index = index

        if best_index is not None and best_similarity >= self._semantic_match_threshold:
            _, answer = qa_pairs[best_index]

            return InferenceResponse(
                action=InferenceAction.RESPOND,
                text=answer,
                source="conversation:semantic_match",
            )

        return InferenceResponse(action=InferenceAction.FALLBACK)
