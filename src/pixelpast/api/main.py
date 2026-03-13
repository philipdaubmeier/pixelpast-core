"""ASGI entrypoint module."""

from pixelpast.api.app import create_app

app = create_app()

__all__ = ["app", "create_app"]
