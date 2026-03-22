"""Filesystem discovery for Google Maps Timeline on-device export ingestion."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pixelpast.ingestion.google_maps_timeline.contracts import (
    GoogleMapsTimelineDocumentDescriptor,
)
from pixelpast.shared.settings import Settings


def resolve_google_maps_timeline_ingestion_root(
    *,
    settings: Settings,
    root: Path | None = None,
) -> Path:
    """Return the configured Google Maps Timeline export root or raise clearly."""

    configured_root = root or settings.google_maps_timeline_root
    if configured_root is None:
        raise ValueError(
            "Google Maps Timeline ingestion requires "
            "PIXELPAST_GOOGLE_MAPS_TIMELINE_ROOT to be configured."
        )
    return configured_root.expanduser().resolve()


class GoogleMapsTimelineDocumentDiscoverer:
    """Discover the one supported Google Maps Timeline export document."""

    def discover_documents(
        self,
        root: Path,
        *,
        on_document_discovered: (
            Callable[[GoogleMapsTimelineDocumentDescriptor, int], None] | None
        ) = None,
    ) -> tuple[GoogleMapsTimelineDocumentDescriptor, ...]:
        """Validate one JSON export file and return it as a deterministic set."""

        resolved_root = root.expanduser().resolve()
        if not resolved_root.exists():
            raise ValueError(
                f"Google Maps Timeline root does not exist: {resolved_root}"
            )
        if not resolved_root.is_file():
            raise ValueError(
                "Google Maps Timeline root must be a file, not a directory: "
                f"{resolved_root}"
            )
        if resolved_root.suffix.lower() != ".json":
            raise ValueError(
                "Google Maps Timeline root must be a .json file: "
                f"{resolved_root}"
            )

        documents = (GoogleMapsTimelineDocumentDescriptor(path=resolved_root),)
        if on_document_discovered is not None:
            on_document_discovered(documents[0], 1)
        return documents


__all__ = [
    "GoogleMapsTimelineDocumentDiscoverer",
    "resolve_google_maps_timeline_ingestion_root",
]
