from datetime import UTC, datetime
from time import perf_counter

from backend.app.domain.analytics.decision_record import DecisionRecord
from backend.app.domain.analytics.repository import DecisionRepository
from backend.app.domain.conversation.scope import ConversationScope
from backend.app.domain.conversation.store import ConversationStore
from backend.app.domain.embedding.provider import EmbeddingProvider
from backend.app.domain.inference import (
    InferenceAction,
    InferenceRequest,
    InferenceResponse,
)
from backend.app.domain.knowledge.repository import AnsweredQuestionRepository
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
        answered_question_repository: AnsweredQuestionRepository,
        decision_repository: DecisionRepository,
        semantic_match_threshold: float,
    ) -> None:
        self._pattern_repository = pattern_repository
        self._conversation_store = conversation_store
        self._embedding_provider = embedding_provider
        self._answered_question_repository = answered_question_repository
        self._decision_repository = decision_repository
        self._semantic_match_threshold = semantic_match_threshold

    async def process(
        self,
        request: InferenceRequest,
    ) -> InferenceResponse:
        """Process an inference request, recording the decision made."""

        start = perf_counter()
        response = await self._decide(request)
        latency_ms = (perf_counter() - start) * 1000

        await self._decision_repository.record(
            DecisionRecord(
                tenant_id=request.tenant_id,
                business_id=request.business_id,
                conversation_id=request.conversation_id,
                action=response.action,
                source=response.source,
                intent=response.intent.value if response.intent is not None else None,
                latency_ms=latency_ms,
                created_at=datetime.now(UTC),
            )
        )

        return response

    async def _decide(
        self,
        request: InferenceRequest,
    ) -> InferenceResponse:
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

        return await self._match_answered_question(request)

    async def _match_answered_question(self, request: InferenceRequest) -> InferenceResponse:
        """Reuse an earlier answer if this question means the same as one
        this business has already had answered before - by anyone, in any
        conversation - even if worded differently."""

        query_vector = (await self._embedding_provider.embed([request.text]))[0]

        match = await self._answered_question_repository.find_most_similar(
            tenant_id=request.tenant_id,
            business_id=request.business_id,
            embedding=query_vector,
        )

        if match is not None:
            answered_question, similarity = match

            if similarity >= self._semantic_match_threshold:
                return InferenceResponse(
                    action=InferenceAction.RESPOND,
                    text=answered_question.answer,
                    source="knowledge:semantic_match",
                )

        return InferenceResponse(action=InferenceAction.FALLBACK)
