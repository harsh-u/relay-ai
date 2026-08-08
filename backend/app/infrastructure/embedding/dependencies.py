from functools import lru_cache

from backend.app.config.settings import get_settings
from backend.app.domain.embedding.provider import EmbeddingProvider
from backend.app.infrastructure.embedding.fastembed_provider import FastEmbedProvider


@lru_cache
def _get_fastembed_provider() -> FastEmbedProvider:
    """Load the embedding model once per process and reuse it."""
    settings = get_settings()
    return FastEmbedProvider(model_dir=settings.embedding_model_dir)


async def get_embedding_provider() -> EmbeddingProvider:
    """Provide the production embedding provider."""
    return _get_fastembed_provider()
