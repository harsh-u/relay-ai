from dataclasses import dataclass
from enum import StrEnum

from backend.app.domain.matching.intent import Intent


class InferenceAction(StrEnum):
    """Action RelayAI wants the upstream voice platform to take."""

    RESPOND = "respond"
    FALLBACK = "fallback"


@dataclass(frozen=True, slots=True)
class InferenceRequest:
    """Normalized request received from a voice platform."""

    business_id: str
    conversation_id: str
    text: str


@dataclass(frozen=True, slots=True)
class InferenceResponse:
    """Decision produced by the RelayAI inference pipeline."""

    action: InferenceAction
    text: str | None = None
    source: str | None = None
    intent: Intent | None = None
