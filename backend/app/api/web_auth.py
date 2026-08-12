from typing import Annotated

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from backend.app.config.settings import Settings, get_settings
from backend.app.domain.users.repository import UserRepository
from backend.app.infrastructure.oauth.dependencies import get_oauth_registry
from backend.app.infrastructure.oauth.identity import (
    OAuthIdentityError,
    extract_github_identity,
    extract_google_identity,
)
from backend.app.infrastructure.users.allowlist import is_email_allowed
from backend.app.infrastructure.users.dependencies import get_user_repository
from backend.app.templating import templates

router = APIRouter(tags=["web-auth"])

_SUPPORTED_PROVIDERS = {"google", "github"}


def _require_known_provider(provider: str) -> None:
    if provider not in _SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=404, detail="Unknown OAuth provider.")


@router.get("/login")
async def login_page(
    request: Request,
    next: Annotated[str | None, Query()] = None,
) -> object:
    """Render the sign-in page - two buttons, one per supported provider."""
    return templates.TemplateResponse(
        request,
        "login.html",
        {"next": next},
    )


def _safe_next_path(next_path: str | None) -> str:
    """Only ever redirect to a same-site relative path - never follow an
    absolute/protocol-relative URL some caller put in `next`, which would
    be an open redirect."""
    if next_path and next_path.startswith("/") and not next_path.startswith("//"):
        return next_path

    return "/dashboard"


@router.get("/auth/{provider}/start")
async def start_oauth(
    provider: str,
    request: Request,
    oauth: Annotated[OAuth, Depends(get_oauth_registry)],
    settings: Annotated[Settings, Depends(get_settings)],
    next: Annotated[str | None, Query()] = None,
) -> object:
    """Redirect to the provider's own consent screen. `next` (where to land
    after a successful login) is stashed in the session now and read back
    in the callback - it can't simply be appended to redirect_uri, since
    providers match that value exactly against what's registered."""
    _require_known_provider(provider)

    if next:
        request.session["oauth_next"] = next

    redirect_uri = str(request.url_for("oauth_callback", provider=provider))
    if settings.app_env == "production" and redirect_uri.startswith("http://"):
        # Cloudflare terminates TLS at its edge and forwards plain HTTP to the
        # origin, so request.url_for() sees "http" - force the scheme providers
        # were actually registered with rather than trusting proxy headers.
        redirect_uri = "https://" + redirect_uri[len("http://") :]
    return await oauth.create_client(provider).authorize_redirect(request, redirect_uri)


@router.get("/auth/{provider}/callback", name="oauth_callback")
async def oauth_callback(
    provider: str,
    request: Request,
    oauth: Annotated[OAuth, Depends(get_oauth_registry)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> object:
    """Exchange the authorization code, resolve the caller's email/subject,
    check it against the beta allowlist, and either sign them in (creating
    a User on first login) or show the beta-denied page."""
    _require_known_provider(provider)

    client = oauth.create_client(provider)
    token = await client.authorize_access_token(request)

    try:
        if provider == "google":
            email, subject = extract_google_identity(token)
        else:
            email, subject = await extract_github_identity(client, token)
    except OAuthIdentityError:
        raise HTTPException(
            status_code=400, detail="Could not read your account details from the provider."
        ) from None

    if not is_email_allowed(email, settings):
        return templates.TemplateResponse(
            request,
            "beta_denied.html",
            {"email": email},
            status_code=403,
        )

    user = await user_repository.find_by_oauth_identity(provider, subject)

    if user is None:
        user = await user_repository.create(email=email, provider=provider, subject=subject)

    request.session["user_id"] = user.id
    next_path = _safe_next_path(request.session.pop("oauth_next", None))

    return RedirectResponse(url=next_path, status_code=302)


@router.post("/logout")
async def logout(request: Request) -> object:
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)
