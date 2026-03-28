"""Single-file discovery for Lightroom Classic catalog ingestion."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pixelpast.ingestion.lightroom_catalog.contracts import LightroomCatalogDescriptor

_SUPPORTED_FILE_EXTENSIONS = frozenset({".lrcat", ".sqlite"})


class LightroomCatalogDiscoverer:
    """Validate one Lightroom catalog file and describe it deterministically."""

    def discover_catalogs(
        self,
        root: Path,
        *,
        on_catalog_discovered: (
            Callable[[LightroomCatalogDescriptor, int], None] | None
        ) = None,
    ) -> tuple[LightroomCatalogDescriptor, ...]:
        """Return the one supported Lightroom catalog file for the configured root."""

        configured_root = root.expanduser()
        resolved_root = configured_root.resolve()
        if not resolved_root.exists():
            raise ValueError(f"Lightroom catalog path does not exist: {resolved_root}")
        if not resolved_root.is_file():
            raise ValueError(
                "Lightroom catalog path must be a file, not a directory: "
                f"{resolved_root}"
            )
        if resolved_root.suffix.lower() not in _SUPPORTED_FILE_EXTENSIONS:
            raise ValueError(
                "Lightroom catalog path must use one of the supported extensions "
                f"{sorted(_SUPPORTED_FILE_EXTENSIONS)}: {resolved_root}"
            )

        catalogs = (
            LightroomCatalogDescriptor(
                path=resolved_root,
                configured_path=configured_root,
            ),
        )
        if on_catalog_discovered is not None:
            on_catalog_discovered(catalogs[0], 1)
        return catalogs


__all__ = ["LightroomCatalogDiscoverer"]
