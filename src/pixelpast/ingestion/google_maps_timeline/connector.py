"""Composition facade for Google Maps Timeline discovery, load, and transform."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from pixelpast.ingestion.google_maps_timeline.contracts import (
    GoogleMapsTimelineDocumentDescriptor,
    GoogleMapsTimelineTransformError,
    LoadedGoogleMapsTimelineExportDocument,
    ParsedGoogleMapsTimelineExport,
)
from pixelpast.ingestion.google_maps_timeline.discovery import (
    GoogleMapsTimelineDocumentDiscoverer,
)
from pixelpast.ingestion.google_maps_timeline.fetch import (
    GoogleMapsTimelineDocumentFetcher,
    GoogleMapsTimelineDocumentLoadProgress,
)
from pixelpast.ingestion.google_maps_timeline.transform import (
    parse_google_maps_timeline_export_document,
    parse_loaded_google_maps_timeline_export_document,
)


class GoogleMapsTimelineConnector:
    """Facade that composes Google Maps Timeline discovery and raw loading."""

    def __init__(
        self,
        *,
        document_discoverer: GoogleMapsTimelineDocumentDiscoverer | None = None,
        document_fetcher: GoogleMapsTimelineDocumentFetcher | None = None,
    ) -> None:
        self._document_discoverer = (
            document_discoverer
            if document_discoverer is not None
            else GoogleMapsTimelineDocumentDiscoverer()
        )
        self._document_fetcher = (
            document_fetcher
            if document_fetcher is not None
            else GoogleMapsTimelineDocumentFetcher()
        )

    def discover_documents(
        self,
        root: Path,
        *,
        on_document_discovered: (
            Callable[[GoogleMapsTimelineDocumentDescriptor, int], None] | None
        ) = None,
    ) -> tuple[GoogleMapsTimelineDocumentDescriptor, ...]:
        """Delegate single-file discovery to the dedicated discoverer."""

        return self._document_discoverer.discover_documents(
            root,
            on_document_discovered=on_document_discovered,
        )

    def fetch_documents(
        self,
        *,
        documents: Sequence[GoogleMapsTimelineDocumentDescriptor],
        on_document_progress: (
            Callable[[GoogleMapsTimelineDocumentLoadProgress], None] | None
        ) = None,
    ) -> tuple[LoadedGoogleMapsTimelineExportDocument, ...]:
        """Load raw export text for the discovered document set."""

        return self._document_fetcher.fetch_documents(
            documents=documents,
            on_document_progress=on_document_progress,
        )

    def parse_document(
        self,
        *,
        document: GoogleMapsTimelineDocumentDescriptor,
        text: str,
    ) -> ParsedGoogleMapsTimelineExport:
        """Parse one raw text document into the explicit semantic contract."""

        return parse_google_maps_timeline_export_document(
            descriptor=document,
            text=text,
        )

    def parse_loaded_document(
        self,
        document: LoadedGoogleMapsTimelineExportDocument,
    ) -> ParsedGoogleMapsTimelineExport:
        """Parse one loaded document payload into the explicit semantic contract."""

        return parse_loaded_google_maps_timeline_export_document(document)

    def build_transform_error(
        self,
        *,
        document: GoogleMapsTimelineDocumentDescriptor,
        error: Exception,
    ) -> GoogleMapsTimelineTransformError:
        """Translate one analysis failure into the stable error contract."""

        return GoogleMapsTimelineTransformError(document=document, message=str(error))


__all__ = ["GoogleMapsTimelineConnector"]
