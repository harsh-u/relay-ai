from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from backend.app.api.analytics import router as analytics_router
from backend.app.api.companies import router as companies_router
from backend.app.api.docs import router as docs_router
from backend.app.api.health import router as health_router
from backend.app.api.inference import router as inference_router
from backend.app.api.knowledge import router as knowledge_router
from backend.app.api.me import router as me_router
from backend.app.api.pages import router as pages_router
from backend.app.api.patterns import router as patterns_router
from backend.app.api.web_auth import router as web_auth_router
from backend.app.config.settings import get_settings
from backend.app.infrastructure.users.dependencies import NotAuthenticatedError

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"


def create_application() -> FastAPI:
    """Create and configure the RelayAI FastAPI application."""
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="AI inference gateway for voice AI platforms.",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    application.add_middleware(SessionMiddleware, secret_key=settings.session_secret_key)

    @application.exception_handler(NotAuthenticatedError)
    async def _redirect_to_login(request: Request, exc: NotAuthenticatedError) -> RedirectResponse:
        return RedirectResponse(url=f"/login?next={exc.next_path}", status_code=302)

    application.include_router(health_router)
    application.include_router(inference_router)
    application.include_router(analytics_router)
    application.include_router(knowledge_router)
    application.include_router(patterns_router)
    application.include_router(companies_router)
    application.include_router(me_router)
    application.include_router(web_auth_router)
    application.include_router(pages_router)
    application.include_router(docs_router)

    if STATIC_DIR.is_dir():
        application.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    if FRONTEND_DIR.is_dir():
        application.mount(
            "/panel",
            StaticFiles(directory=FRONTEND_DIR, html=True),
            name="panel",
        )

    return application


app = create_application()
