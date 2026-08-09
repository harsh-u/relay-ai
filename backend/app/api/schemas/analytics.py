from pydantic import BaseModel, Field


class DecisionSummaryResponse(BaseModel):
    """How often RelayAI avoided the LLM for a business, and via what."""

    total: int = Field(description="Total /v1/inference requests recorded for this business.")
    respond_count: int = Field(description="Requests RelayAI answered directly, without the LLM.")
    fallback_count: int = Field(description="Requests that needed the caller's own LLM.")
    avoided_llm_rate: float = Field(
        description="respond_count / total - the share of traffic RelayAI handled on its own.",
        examples=[0.42],
    )
    respond_by_source: dict[str, int] = Field(
        description=(
            "Breakdown of respond_count by which mechanism answered - e.g. "
            "'builtin:greeting', 'conversation:last_response', "
            "'knowledge:semantic_match'."
        ),
        examples=[{"builtin:greeting": 12, "knowledge:semantic_match": 8}],
    )
