from functools import lru_cache

from authlib.integrations.starlette_client import OAuth

from backend.app.config.settings import get_settings
from backend.app.infrastructure.oauth.client import build_oauth_registry


@lru_cache
def get_oauth_registry() -> OAuth:
    """Provide the production OAuth client registry. Cached like
    `get_settings()` - registering clients is cheap but pointless to
    redo per request. Tests override this dependency entirely with a
    fake registry rather than hitting Google/GitHub for real."""
    return build_oauth_registry(get_settings())
