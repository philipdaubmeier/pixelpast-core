"""ASGI entrypoint module."""

from pixelpast.api.app import app, create_app

__all__ = ["app", "create_app"]
