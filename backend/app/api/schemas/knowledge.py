from pydantic import BaseModel


class ClearKnowledgeCacheResponse(BaseModel):
    """Result of clearing a business's (or one agent's) cached answers."""

    deleted: int
