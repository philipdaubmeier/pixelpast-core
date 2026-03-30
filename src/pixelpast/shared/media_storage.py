"""Helpers for runtime media storage validation."""

from __future__ import annotations

from pathlib import Path

from pixelpast.shared.settings import Settings


def require_media_thumb_root(*, settings: Settings) -> Path:
    """Return a usable resolved thumbnail root or raise a clear config error."""

    configured_root = settings.media_thumb_root
    if configured_root is None:
        raise ValueError(
            "Asset ingestion requires PIXELPAST_MEDIA_THUMB_ROOT to be configured."
        )

    resolved_root = configured_root.expanduser().resolve()
    try:
        resolved_root.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise ValueError(
            "Asset ingestion requires PIXELPAST_MEDIA_THUMB_ROOT to point to a "
            f"usable directory: {resolved_root.as_posix()}"
        ) from error

    if not resolved_root.is_dir():
        raise ValueError(
            "Asset ingestion requires PIXELPAST_MEDIA_THUMB_ROOT to point to a "
            f"directory: {resolved_root.as_posix()}"
        )

    return resolved_root


__all__ = ["require_media_thumb_root"]
