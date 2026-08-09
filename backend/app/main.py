from fastapi import FastAPI

from backend.app.api.analytics import router as analytics_router
from backend.app.api.health import router as health_router
from backend.app.api.inference import router as inference_router
from backend.app.api.knowledge import router as knowledge_router
from backend.app.api.patterns import router as patterns_router
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
    application.include_router(inference_router)
    application.include_router(analytics_router)
    application.include_router(knowledge_router)
    application.include_router(patterns_router)

    return application


app = create_application()
