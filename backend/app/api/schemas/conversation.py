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
