from pydantic import BaseModel, Field

from backend.app.domain.inference import InferenceAction
from backend.app.domain.matching.intent import Intent


class InferenceRequestBody(BaseModel):
    """HTTP request received from a voice platform."""

    business_id: str = Field(min_length=1)
    conversation_id: str = Field(min_length=1)
    text: str


class InferenceResponseBody(BaseModel):
    """HTTP response returned to a voice platform."""

    action: InferenceAction
    text: str | None = None
    source: str | None = None
    intent: Intent | None = None
