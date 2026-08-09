from dataclasses import dataclass
from datetime import datetime

from backend.app.domain.inference import InferenceAction


@dataclass(frozen=True, slots=True)
class DecisionRecord:
    """A single inference decision, for measuring how often the LLM is avoided."""

    tenant_id: str
    business_id: str
    conversation_id: str
    agent_id: str
    action: InferenceAction
    source: str | None
    intent: str | None
    latency_ms: float
    created_at: datetime
