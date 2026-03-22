"""Raw export loading for discovered Google Maps Timeline documents."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from pixelpast.ingestion.google_maps_timeline.contracts import (
    GoogleMapsTimelineDocumentDescriptor,
    LoadedGoogleMapsTimelineExportDocument,
)


@dataclass(slots=True, frozen=True)
class GoogleMapsTimelineDocumentLoadProgress:
    """Represents one raw Google Maps Timeline document load transition."""

    event: str
    document: GoogleMapsTimelineDocumentDescriptor
    document_index: int
    document_total: int


class GoogleMapsTimelineDocumentFetcher:
    """Load raw UTF-8 JSON text for discovered Google Maps Timeline documents."""

    def fetch_documents(
        self,
        *,
        documents: Sequence[GoogleMapsTimelineDocumentDescriptor],
        on_document_progress: (
            Callable[[GoogleMapsTimelineDocumentLoadProgress], None] | None
        ) = None,
    ) -> tuple[LoadedGoogleMapsTimelineExportDocument, ...]:
        """Return loaded raw export documents in deterministic input order."""

        loaded_documents: list[LoadedGoogleMapsTimelineExportDocument] = []
        document_total = len(documents)
        for index, document in enumerate(documents, start=1):
            if on_document_progress is not None:
                on_document_progress(
                    GoogleMapsTimelineDocumentLoadProgress(
                        event="submitted",
                        document=document,
                        document_index=index,
                        document_total=document_total,
                    )
                )
            loaded_documents.append(
                LoadedGoogleMapsTimelineExportDocument(
                    descriptor=document,
                    text=document.path.read_text(encoding="utf-8"),
                )
            )
            if on_document_progress is not None:
                on_document_progress(
                    GoogleMapsTimelineDocumentLoadProgress(
                        event="completed",
                        document=document,
                        document_index=index,
                        document_total=document_total,
                    )
                )
        return tuple(loaded_documents)


__all__ = [
    "GoogleMapsTimelineDocumentFetcher",
    "GoogleMapsTimelineDocumentLoadProgress",
]
