from pydantic import BaseModel, Field


class InferenceRequestBody(BaseModel):
    tenant_id: str = Field(min_length=1)
    business_id: str = Field(min_length=1)
    conversation_id: str = Field(min_length=1)
    text: str


class InferenceResponseBody(BaseModel):
    action: str
    text: str | None = None
    source: str | None = None
    intent: str | None = None
