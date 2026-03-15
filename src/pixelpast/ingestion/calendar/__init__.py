"""Calendar ingestion contracts and transform helpers."""

from pixelpast.ingestion.calendar.contracts import (
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
from pixelpast.ingestion.calendar.transform import (
    build_calendar_event_candidates,
    build_calendar_source_candidate,
    parse_calendar_document,
)

__all__ = [
    "CalendarDocumentDescriptor",
    "CalendarDocumentDiscoverer",
    "CalendarDocumentFetcher",
    "CalendarDocumentLoadProgress",
    "CalendarEventCandidate",
    "CalendarIngestionResult",
    "CalendarParsedProperty",
    "CalendarSourceCandidate",
    "CalendarTransformError",
    "ParsedCalendarDocument",
    "ParsedCalendarEvent",
    "build_calendar_event_candidates",
    "build_calendar_source_candidate",
    "parse_calendar_document",
]
