from pydantic import BaseModel, Field

from backend.app.domain.business.knowledge_scope import KnowledgeScope


class ClearKnowledgeCacheResponse(BaseModel):
    """Result of clearing a business's (or one agent's) cached answers."""

    deleted: int = Field(
        description="Number of cached answers actually removed.",
        examples=[3],
    )


class UpdateKnowledgeSettingsRequest(BaseModel):
    """Change how a business's knowledge cache behaves. Only the fields you
    set are changed - omit a field (or send it as null) to leave it as is."""

    tenant_id: str = Field(
        min_length=1,
        description="The tenant this business belongs to.",
        examples=["11111111-1111-1111-1111-111111111111"],
    )
    business_id: str = Field(
        min_length=1,
        description="The business to configure.",
        examples=["22222222-2222-2222-2222-222222222222"],
    )
    knowledge_scope: KnowledgeScope | None = Field(
        default=None,
        description=(
            "'shared' pools every agent's cached answers together for this "
            "business (the default). 'isolated' means each agent_id only "
            "reuses its own cached answers, never another agent's."
        ),
        examples=["isolated"],
    )
    knowledge_ttl_days: int | None = Field(
        default=None,
        ge=0,
        description=(
            "How many days a cached answer stays eligible for reuse before "
            "it's treated as stale and ignored (not deleted - just no "
            "longer matched). 0 means answers are effectively never reused. "
            "Falls back to the global default (30) if never set."
        ),
        examples=[14],
    )


class UpdateKnowledgeSettingsResponse(BaseModel):
    """The resulting settings now in effect for this business."""

    knowledge_scope: KnowledgeScope
    knowledge_ttl_days: int


class AddAnsweredQuestionRequest(BaseModel):
    """Directly seed the knowledge cache with a known (question, answer)
    pair - e.g. to pre-load a business's common FAQs instead of waiting for
    a real caller to trigger a fallback-then-report round trip first."""

    tenant_id: str = Field(
        min_length=1,
        description="The tenant this business belongs to.",
        examples=["11111111-1111-1111-1111-111111111111"],
    )
    business_id: str = Field(
        min_length=1,
        description="The business this answer belongs to.",
        examples=["22222222-2222-2222-2222-222222222222"],
    )
    agent_id: str = Field(
        default="default",
        min_length=1,
        description=(
            "Only meaningful if this business is in 'isolated' scope - "
            "which agent's cache this answer is seeded into. Ignored (all "
            "agents share it) in 'shared' scope, the default."
        ),
    )
    question: str = Field(
        min_length=1,
        description=(
            "A representative phrasing of the question - future callers "
            "don't need to match it exactly, just closely enough in meaning."
        ),
        examples=["Do you accept Delta Dental insurance?"],
    )
    answer: str = Field(
        min_length=1,
        description=(
            "The answer to serve whenever a caller's question is "
            "recognized as similar enough to this one."
        ),
        examples=["Yes, we're in-network with Delta Dental PPO."],
    )


class AddAnsweredQuestionResponse(BaseModel):
    """Confirmation that the answer is now cached and reusable."""

    stored: bool = True
