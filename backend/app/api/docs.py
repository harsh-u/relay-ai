from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse

from backend.app.config.settings import Settings, get_settings
from backend.app.domain.users.user import User
from backend.app.infrastructure.users.dependencies import (
    require_current_user_for_api,
    require_current_user_for_page,
)

router = APIRouter(include_in_schema=False, tags=["docs"])


@router.get("/openapi.json")
async def openapi_schema(
    request: Request,
    current_user: Annotated[User, Depends(require_current_user_for_api)],
) -> JSONResponse:
    """The OpenAPI schema itself - fetched by /docs' own JS, so a 401
    (not a redirect) is the right response when signed out."""
    return JSONResponse(request.app.openapi())


@router.get("/docs")
async def docs_page(
    current_user: Annotated[User, Depends(require_current_user_for_page)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> HTMLResponse:
    """Interactive API docs (Swagger UI) - gated behind login since a real
    API key is needed to use "Try it out", and this is otherwise the same
    default UI FastAPI would serve unauthenticated at docs_url."""
    return get_swagger_ui_html(openapi_url="/openapi.json", title=f"{settings.app_name} API Docs")
