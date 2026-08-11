from datetime import datetime

from pydantic import BaseModel, Field


class AssistantMessageRequest(BaseModel):
    """The answer your own LLM produced for a `fallback` turn - report it
    back so RelayAI can reuse it later (for "repeat that" in this call, and
    for any future caller asking this business something similar)."""

    tenant_id: str = Field(
        min_length=1,
        description="The tenant this business belongs to.",
        examples=["11111111-1111-1111-1111-111111111111"],
    )
    business_id: str = Field(
        min_length=1,
        description="The business this call belongs to.",
        examples=["22222222-2222-2222-2222-222222222222"],
    )
    agent_id: str = Field(
        default="default",
        min_length=1,
        description="The same agent_id used for this call's /v1/inference requests.",
    )
    text: str = Field(
        min_length=1,
        description="The answer your LLM gave for the question it was asked.",
        examples=["Yes, we're in-network with Delta Dental PPO."],
    )


class AssistantMessageResponse(BaseModel):
    """Confirmation that the answer was stored."""

    conversation_id: str
    stored: bool
    cached: bool = Field(
        description=(
            "Whether this answer was also added to the semantic knowledge "
            "cache for future reuse. False when the question it answers was "
            "itself a recognized intent (e.g. 'repeat that' with no prior "
            "context) rather than a genuine unanswered business question."
        ),
    )


class ConversationTurnResponse(BaseModel):
    """One turn of a conversation - what was said, and for a user turn, how
    RelayAI decided to answer it."""

    role: str = Field(description="'user' or 'assistant'.", examples=["user"])
    text: str
    created_at: datetime
    action: str | None = Field(
        default=None,
        description="'respond' or 'fallback' - only present for a 'user' turn.",
        examples=["respond"],
    )
    source: str | None = Field(
        default=None,
        description="Which mechanism answered, if action was 'respond'.",
        examples=["knowledge:semantic_match"],
    )
    intent: str | None = None
    similarity: float | None = Field(
        default=None,
        description="Cosine similarity to the closest cached question considered, if any.",
    )
    matched_question: str | None = Field(
        default=None,
        description="The cached question compared against, if any.",
    )


class ConversationHistoryResponse(BaseModel):
    """A conversation's full transcript, each user turn annotated with how
    RelayAI decided to answer it - for reviewing after the fact how a real
    or simulated call actually went, not just watching it live.

    Turns are paired with their decision by position (Nth user turn <-> Nth
    recorded decision), since a fallback on an empty/whitespace transcribed
    turn is recorded as a decision without ever saving a user message - a
    rare edge case that can shift the pairing by one for the rest of the
    conversation. Good enough for review; not a source of truth for billing
    or auditing.
    """

    conversation_id: str
    turns: list[ConversationTurnResponse]
