from pydantic import BaseModel, Field


class ClearKnowledgeCacheResponse(BaseModel):
    """Result of clearing a business's (or one agent's) cached answers."""

    deleted: int = Field(
        description="Number of cached answers actually removed.",
        examples=[3],
    )
