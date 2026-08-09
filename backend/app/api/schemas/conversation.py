from pydantic import BaseModel, Field


class AssistantMessageRequest(BaseModel):
    """Assistant message received from an upstream LLM/voice system."""

    tenant_id: str = Field(min_length=1)
    business_id: str = Field(min_length=1)
    agent_id: str = Field(default="default", min_length=1)
    text: str = Field(min_length=1)


class AssistantMessageResponse(BaseModel):
    """Result of storing an assistant message."""

    conversation_id: str
    stored: bool
