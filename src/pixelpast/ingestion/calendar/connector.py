"""Composition facade for calendar discovery, fetch, and transform."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from pixelpast.ingestion.calendar.contracts import (
    CalendarDocumentCandidate,
    CalendarDocumentDescriptor,
    CalendarTransformError,
)
from pixelpast.ingestion.calendar.discovery import CalendarDocumentDiscoverer
from pixelpast.ingestion.calendar.fetch import (
    CalendarDocumentFetcher,
    CalendarDocumentLoadProgress,
)
from pixelpast.ingestion.calendar.transform import (
    build_calendar_event_candidates,
    build_calendar_source_candidate,
    parse_calendar_document,
)


class CalendarConnector:
    """Facade that composes calendar discovery, fetch, and transform stages."""

    def __init__(
        self,
        *,
        document_discoverer: CalendarDocumentDiscoverer | None = None,
        document_fetcher: CalendarDocumentFetcher | None = None,
    ) -> None:
        self._document_discoverer = (
            document_discoverer
            if document_discoverer is not None
            else CalendarDocumentDiscoverer()
        )
        self._document_fetcher = (
            document_fetcher
            if document_fetcher is not None
            else CalendarDocumentFetcher()
        )

    def discover_documents(
        self,
        root: Path,
        *,
        on_document_discovered: Callable[[CalendarDocumentDescriptor, int], None]
        | None = None,
    ) -> list[CalendarDocumentDescriptor]:
        """Delegate document discovery to the dedicated discoverer component."""

        return self._document_discoverer.discover_documents(
            root,
            on_document_discovered=on_document_discovered,
        )

    def fetch_text_by_descriptor(
        self,
        *,
        documents: Sequence[CalendarDocumentDescriptor],
        on_document_progress: (
            Callable[[CalendarDocumentLoadProgress], None] | None
        ) = None,
    ) -> dict[CalendarDocumentDescriptor, str]:
        """Load raw calendar text for the discovered document set."""

        return self._document_fetcher.fetch_text_by_descriptor(
            documents=documents,
            on_document_progress=on_document_progress,
        )

    def build_document_candidate(
        self,
        *,
        document: CalendarDocumentDescriptor,
        text: str,
    ) -> CalendarDocumentCandidate:
        """Build one persistable calendar document candidate."""

        parsed_document = parse_calendar_document(
            descriptor=document,
            text=text,
        )
        return CalendarDocumentCandidate(
            document=document,
            source=build_calendar_source_candidate(parsed_document),
            events=build_calendar_event_candidates(parsed_document),
        )

    def build_transform_error(
        self,
        *,
        document: CalendarDocumentDescriptor,
        error: Exception,
    ) -> CalendarTransformError:
        """Translate one analysis failure into the stable calendar error contract."""

        return CalendarTransformError(document=document, message=str(error))


__all__ = ["CalendarConnector"]
