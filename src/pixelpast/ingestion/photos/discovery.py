"""Filesystem discovery components and discovery-facing contracts."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pixelpast.ingestion.photos.contracts import (
    PhotoAssetCandidate,
    PhotoDiscoveryError,
    PhotoDiscoveryResult,
)

_SUPPORTED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".heic"})


class PhotoFileDiscoverer:
    """Discover supported photo files beneath a configured filesystem root."""

    def discover_paths(
        self,
        root: Path,
        *,
        on_path_discovered: Callable[[Path, int], None] | None = None,
    ) -> list[Path]:
        """Return supported file paths beneath a validated root directory."""

        resolved_root = root.expanduser().resolve()
        if not resolved_root.exists():
            raise ValueError(f"Photo root does not exist: {resolved_root}")
        if not resolved_root.is_dir():
            raise ValueError(f"Photo root is not a directory: {resolved_root}")

        supported_paths: list[Path] = []
        for path in sorted(resolved_root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in _SUPPORTED_EXTENSIONS:
                continue
            supported_paths.append(path)
            if on_path_discovered is not None:
                on_path_discovered(path, len(supported_paths))
        return supported_paths


__all__ = [
    "PhotoAssetCandidate",
    "PhotoDiscoveryError",
    "PhotoDiscoveryResult",
    "PhotoFileDiscoverer",
]
