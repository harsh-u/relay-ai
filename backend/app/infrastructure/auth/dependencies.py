from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.domain.auth.hashing import hash_key
from backend.app.domain.auth.repository import ApiKeyRepository
from backend.app.infrastructure.auth.postgres import PostgresApiKeyRepository

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_api_key_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiKeyRepository:
    """Provide the production API key repository."""
    return PostgresApiKeyRepository(session)


async def get_authenticated_tenant_id(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(_bearer_scheme),
    ],
    api_key_repository: Annotated[
        ApiKeyRepository,
        Depends(get_api_key_repository),
    ],
) -> str:
    """Resolve the tenant_id for the caller's API key, or raise a clear 401.

    Uses HTTPBearer(auto_error=False) so a missing (or non-Bearer) header
    is reported here with an explicit message, instead of HTTPBearer's own
    default bare 403 - while still surfacing as a proper "Authorize" button
    in /docs. A missing header and a malformed one (wrong scheme, empty
    token) are indistinguishable to HTTPBearer itself, so both fall into
    this same branch.
    """
    if credentials is None or not credentials.credentials.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header. Expected 'Authorization: Bearer <api key>'.",
        )

    key_hash = hash_key(credentials.credentials)
    api_key = await api_key_repository.find_active_by_hash(key_hash)

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key.",
        )

    return api_key.tenant_id
