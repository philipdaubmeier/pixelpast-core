"""FastAPI application factory."""

from fastapi import FastAPI

from pixelpast.api.router import create_api_router
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application and shared runtime dependencies."""

    runtime = create_runtime_context(settings=settings or get_settings())
    initialize_database(runtime)

    app = FastAPI(
        title=runtime.settings.app_name,
        debug=runtime.settings.debug,
    )
    app.state.settings = runtime.settings
    app.state.session_factory = runtime.session_factory
    app.include_router(create_api_router())
    return app


app = create_app()
