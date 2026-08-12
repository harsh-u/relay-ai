from typing import Annotated

from fastapi import APIRouter, Depends, Request

from backend.app.domain.users.user import User
from backend.app.infrastructure.users.dependencies import (
    get_current_user_or_none,
    require_current_user_for_page,
)
from backend.app.templating import templates

router = APIRouter(tags=["pages"])


@router.get("/")
async def homepage(
    request: Request,
    current_user: Annotated[User | None, Depends(get_current_user_or_none)],
) -> object:
    """The marketing landing page - public, no login required."""
    return templates.TemplateResponse(request, "index.html", {"current_user": current_user})


@router.get("/dashboard")
async def dashboard_page(
    request: Request,
    current_user: Annotated[User, Depends(require_current_user_for_page)],
) -> object:
    """Logged-in home: list/create companies, see a freshly minted API
    key once. Redirects to /login (via the NotAuthenticatedError
    exception handler) if there's no valid session."""
    return templates.TemplateResponse(request, "dashboard.html", {"current_user": current_user})


@router.get("/console")
async def console_page(
    request: Request,
    current_user: Annotated[User, Depends(require_current_user_for_page)],
) -> object:
    """A login-gated, self-service version of the internal /panel test
    tool - scoped to the signed-in user's own companies (/v1/me/companies)
    rather than every company that exists."""
    return templates.TemplateResponse(request, "console.html", {"current_user": current_user})
