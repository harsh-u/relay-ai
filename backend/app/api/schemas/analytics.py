from pydantic import BaseModel


class DecisionSummaryResponse(BaseModel):
    """How often RelayAI avoided the LLM for a business, and via what."""

    total: int
    respond_count: int
    fallback_count: int
    avoided_llm_rate: float
    respond_by_source: dict[str, int]
