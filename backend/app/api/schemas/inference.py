from pydantic import BaseModel, Field


class InferenceRequestBody(BaseModel):
    """A transcribed STT turn to run through RelayAI's decision layer."""

    business_id: str = Field(
        min_length=1,
        description="The business this call belongs to.",
        examples=["22222222-2222-2222-2222-222222222222"],
    )
    conversation_id: str = Field(
        min_length=1,
        description="A stable ID for this call - e.g. your voice platform's room/session ID.",
        examples=["call-8492"],
    )
    agent_id: str = Field(
        default="default",
        min_length=1,
        description=(
            "Which of this business's agents is handling the call. Only "
            "matters if the business is in 'isolated' knowledge scope - "
            "otherwise safe to leave as the default."
        ),
    )
    text: str = Field(
        description="The caller's transcribed speech for this turn.",
        examples=["Do you accept Delta Dental insurance?"],
    )


class InferenceResponseBody(BaseModel):
    """RelayAI's decision for this turn."""

    action: str = Field(
        description=(
            "'respond': speak `text` directly, skip your LLM. "
            "'fallback': RelayAI has no answer - call your own LLM as usual."
        ),
        examples=["respond"],
    )
    text: str | None = Field(
        default=None,
        description="The text to speak, present only when action is 'respond'.",
        examples=["Hello! How can I help you?"],
    )
    source: str | None = Field(
        default=None,
        description=(
            "Which mechanism produced this answer, e.g. 'builtin:greeting', "
            "'conversation:last_response', or 'knowledge:semantic_match'. "
            "None when action is 'fallback'."
        ),
        examples=["builtin:greeting"],
    )
    intent: str | None = Field(
        default=None,
        description="The recognized intent, if a builtin rule matched (e.g. 'greeting').",
        examples=["greeting"],
    )
    similarity: float | None = Field(
        default=None,
        description=(
            "Cosine similarity (0-1) to the closest cached knowledge-cache "
            "question considered for this turn, for observability. Present "
            "when source is 'knowledge:semantic_match' (it met the match "
            "threshold) or when action is 'fallback' but a cached question "
            "existed and came close without meeting it. None when no "
            "cached questions existed to compare against, or when a "
            "builtin rule / conversation recall answered before the "
            "knowledge cache was ever consulted."
        ),
        examples=[0.812],
    )
    matched_question: str | None = Field(
        default=None,
        description=(
            "The cached question this turn was compared against - the one "
            "actually reused (source is 'knowledge:semantic_match') or the "
            "closest candidate that came up short on a fallback. Lets you "
            "see exactly which prior question this turn is being judged "
            "against, not just how similar it was. None under the same "
            "conditions as `similarity`."
        ),
        examples=["Do you accept Delta Dental insurance?"],
    )
