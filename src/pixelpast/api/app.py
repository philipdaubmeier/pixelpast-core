"""FastAPI application factory."""

from fastapi import FastAPI

from pixelpast.api.router import create_api_router
from pixelpast.persistence.session import create_session_factory
from pixelpast.shared.settings import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application and shared runtime dependencies."""

    runtime_settings = settings or get_settings()
    session_factory = create_session_factory(settings=runtime_settings)

    app = FastAPI(
        title=runtime_settings.app_name,
        debug=runtime_settings.debug,
    )
    app.state.settings = runtime_settings
    app.state.session_factory = session_factory
    app.include_router(create_api_router())
    return app


app = create_app()
