"""Top-level API router registration."""

from fastapi import APIRouter

from pixelpast.api.routes.bootstrap_ui import router as bootstrap_ui_router
from pixelpast.api.routes.day_detail import router as day_detail_router
from pixelpast.api.routes.daygrid import router as daygrid_router
from pixelpast.api.routes.health import router as health_router
from pixelpast.api.routes.hovercontext import router as hovercontext_router
from pixelpast.api.routes.manage_data import router as manage_data_router
from pixelpast.api.routes.media import router as media_router
from pixelpast.api.routes.social_graph import router as social_graph_router


def create_api_router() -> APIRouter:
    """Create the application router with all endpoint modules registered."""

    router = APIRouter()
    api_router = APIRouter(prefix="/api")
    api_router.include_router(health_router)
    api_router.include_router(bootstrap_ui_router)
    api_router.include_router(daygrid_router)
    api_router.include_router(hovercontext_router)
    api_router.include_router(day_detail_router)
    api_router.include_router(social_graph_router)
    api_router.include_router(manage_data_router)
    router.include_router(api_router)
    router.include_router(media_router)
    return router
