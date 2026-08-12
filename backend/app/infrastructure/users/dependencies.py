from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.domain.users.repository import UserRepository
from backend.app.domain.users.user import User
from backend.app.infrastructure.users.postgres import PostgresUserRepository


class NotAuthenticatedError(Exception):
    """Raised by `require_current_user_for_page` when a page route is
    visited with no valid session - caught by an exception handler in
    main.py that redirects to /login instead of returning a raw error."""

    def __init__(self, next_path: str) -> None:
        self.next_path = next_path


async def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserRepository:
    """Provide the production user repository."""
    return PostgresUserRepository(session)


async def get_current_user_or_none(
    request: Request,
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> User | None:
    """Resolve the logged-in user from the session cookie, or None if
    there isn't one - for pages that render differently either way
    (e.g. the marketing homepage) without forcing a login."""

    user_id = request.session.get("user_id")

    if user_id is None:
        return None

    return await user_repository.get_by_id(user_id)


async def require_current_user_for_page(
    request: Request,
    current_user: Annotated[User | None, Depends(get_current_user_or_none)],
) -> User:
    """For full HTML page routes (e.g. /dashboard) - raises
    NotAuthenticatedError instead of returning None, so the caller
    never has to null-check; main.py's exception handler turns that
    into a redirect to /login?next=<path>."""

    if current_user is None:
        raise NotAuthenticatedError(next_path=request.url.path)

    return current_user


async def require_current_user_for_api(
    request: Request,
    current_user: Annotated[User | None, Depends(get_current_user_or_none)],
) -> User:
    """For JSON endpoints under /v1/me/* - raises a plain 401 instead of
    redirecting, since these are called via fetch() from the dashboard's
    own JS, which reacts to a 401 by redirecting client-side itself."""

    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not signed in.")

    return current_user
