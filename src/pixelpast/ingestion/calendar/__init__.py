"""Calendar ingestion contracts and transform helpers."""

from pixelpast.ingestion.calendar.connector import CalendarConnector
from pixelpast.ingestion.calendar.contracts import (
    CalendarDocumentCandidate,
    CalendarDocumentDescriptor,
    CalendarEventCandidate,
    CalendarIngestionResult,
    CalendarParsedProperty,
    CalendarSourceCandidate,
    CalendarTransformError,
    ParsedCalendarDocument,
    ParsedCalendarEvent,
)
from pixelpast.ingestion.calendar.discovery import CalendarDocumentDiscoverer
from pixelpast.ingestion.calendar.fetch import (
    CalendarDocumentFetcher,
    CalendarDocumentLoadProgress,
)
from pixelpast.ingestion.calendar.lifecycle import CalendarIngestionRunCoordinator
from pixelpast.ingestion.calendar.persist import CalendarDocumentPersister
from pixelpast.ingestion.calendar.progress import (
    CalendarIngestionProgressSnapshot,
    CalendarIngestionProgressTracker,
)
from pixelpast.ingestion.calendar.service import CalendarIngestionService
from pixelpast.ingestion.calendar.staged import (
    CalendarIngestionPersistenceScope,
    CalendarStagedIngestionStrategy,
)
from pixelpast.ingestion.calendar.transform import (
    build_calendar_event_candidates,
    build_calendar_source_candidate,
    parse_calendar_document,
)

__all__ = [
    "CalendarDocumentDescriptor",
    "CalendarDocumentCandidate",
    "CalendarDocumentDiscoverer",
    "CalendarDocumentFetcher",
    "CalendarDocumentLoadProgress",
    "CalendarDocumentPersister",
    "CalendarConnector",
    "CalendarEventCandidate",
    "CalendarIngestionResult",
    "CalendarIngestionPersistenceScope",
    "CalendarIngestionProgressSnapshot",
    "CalendarIngestionProgressTracker",
    "CalendarIngestionRunCoordinator",
    "CalendarIngestionService",
    "CalendarParsedProperty",
    "CalendarStagedIngestionStrategy",
    "CalendarSourceCandidate",
    "CalendarTransformError",
    "ParsedCalendarDocument",
    "ParsedCalendarEvent",
    "build_calendar_event_candidates",
    "build_calendar_source_candidate",
    "parse_calendar_document",
]
