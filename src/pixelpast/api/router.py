"""Top-level API router registration."""

from fastapi import APIRouter

from pixelpast.api.routes.health import router as health_router


def create_api_router() -> APIRouter:
    """Create the application router with all endpoint modules registered."""

    router = APIRouter()
    router.include_router(health_router)
    return router
