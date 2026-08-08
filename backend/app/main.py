from fastapi import FastAPI

from backend.app.api.health import router as health_router
from backend.app.config.settings import get_settings


def create_application() -> FastAPI:
    """Create and configure the RelayAI FastAPI application."""
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="AI inference gateway for voice AI platforms.",
    )

    application.include_router(health_router)

    return application


app = create_application()
