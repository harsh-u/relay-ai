from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Return the current API health status."""
    return {
        "status": "ok",
        "service": "relay-ai",
    }
