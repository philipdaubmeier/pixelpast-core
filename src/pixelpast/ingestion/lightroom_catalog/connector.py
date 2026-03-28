"""Composition facade for Lightroom catalog discovery and raw loading."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from pixelpast.ingestion.lightroom_catalog.contracts import (
    LoadedLightroomCatalog,
    LightroomCatalogDescriptor,
)
from pixelpast.ingestion.lightroom_catalog.discovery import LightroomCatalogDiscoverer
from pixelpast.ingestion.lightroom_catalog.fetch import (
    LightroomCatalogFetcher,
    LightroomCatalogLoadProgress,
)


class LightroomCatalogConnector:
    """Facade that composes Lightroom catalog discovery and read-only loading."""

    def __init__(
        self,
        *,
        catalog_discoverer: LightroomCatalogDiscoverer | None = None,
        catalog_fetcher: LightroomCatalogFetcher | None = None,
    ) -> None:
        self._catalog_discoverer = (
            catalog_discoverer
            if catalog_discoverer is not None
            else LightroomCatalogDiscoverer()
        )
        self._catalog_fetcher = (
            catalog_fetcher
            if catalog_fetcher is not None
            else LightroomCatalogFetcher()
        )

    def discover_catalogs(
        self,
        root: Path,
        *,
        on_catalog_discovered: (
            Callable[[LightroomCatalogDescriptor, int], None] | None
        ) = None,
    ) -> tuple[LightroomCatalogDescriptor, ...]:
        """Delegate single-file catalog discovery to the dedicated discoverer."""

        return self._catalog_discoverer.discover_catalogs(
            root,
            on_catalog_discovered=on_catalog_discovered,
        )

    def fetch_catalogs(
        self,
        *,
        catalogs: Sequence[LightroomCatalogDescriptor],
        on_catalog_progress: (
            Callable[[LightroomCatalogLoadProgress], None] | None
        ) = None,
    ) -> tuple[LoadedLightroomCatalog, ...]:
        """Load raw Lightroom catalog payloads for the discovered catalog set."""

        return self._catalog_fetcher.fetch_catalogs(
            catalogs=catalogs,
            on_catalog_progress=on_catalog_progress,
        )


__all__ = ["LightroomCatalogConnector"]
