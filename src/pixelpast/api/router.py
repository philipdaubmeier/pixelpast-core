"""Top-level API router registration."""

from fastapi import APIRouter

from pixelpast.api.routes.bootstrap_ui import router as bootstrap_ui_router
from pixelpast.api.routes.day_detail import router as day_detail_router
from pixelpast.api.routes.daygrid import router as daygrid_router
from pixelpast.api.routes.health import router as health_router
from pixelpast.api.routes.hovercontext import router as hovercontext_router
from pixelpast.api.routes.manage_data import router as manage_data_router
from pixelpast.api.routes.social_graph import router as social_graph_router


def create_api_router() -> APIRouter:
    """Create the application router with all endpoint modules registered."""

    router = APIRouter(prefix="/api")
    router.include_router(health_router)
    router.include_router(bootstrap_ui_router)
    router.include_router(daygrid_router)
    router.include_router(hovercontext_router)
    router.include_router(day_detail_router)
    router.include_router(social_graph_router)
    router.include_router(manage_data_router)
    return router
