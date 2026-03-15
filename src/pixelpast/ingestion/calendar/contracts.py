"""Public data contracts for calendar ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True, frozen=True)
class CalendarDocumentDescriptor:
    """One discovered calendar document, optionally backed by an archive member."""

    path: Path
    archive_member_path: str | None = None


@dataclass(slots=True, frozen=True)
class CalendarParsedProperty:
    """One parsed iCalendar property with normalized parameters."""

    name: str
    value: str
    parameters: tuple[tuple[str, str], ...] = ()

    def get_parameter(self, name: str) -> str | None:
        """Return one property parameter by case-insensitive name."""

        normalized_name = name.upper()
        for parameter_name, parameter_value in self.parameters:
            if parameter_name.upper() == normalized_name:
                return parameter_value
        return None


@dataclass(slots=True, frozen=True)
class ParsedCalendarEvent:
    """Parsed VEVENT payload before canonical transformation."""

    uid: str | None
    starts_at: datetime
    ends_at: datetime | None
    summary: str | None
    alt_description: str | None
    alt_description_format: str | None
    properties: tuple[CalendarParsedProperty, ...] = ()


@dataclass(slots=True, frozen=True)
class ParsedCalendarDocument:
    """Parsed calendar-level metadata and VEVENT payloads for one document."""

    descriptor: CalendarDocumentDescriptor
    calendar_name_header: str | None
    calendar_name: str | None
    calendar_external_id_header: str | None
    calendar_external_id: str | None
    timezone_ids: tuple[str, ...]
    properties: tuple[CalendarParsedProperty, ...]
    events: tuple[ParsedCalendarEvent, ...]


@dataclass(slots=True, frozen=True)
class CalendarSourceCandidate:
    """Canonical source candidate derived from one calendar document."""

    type: str
    name: str | None
    external_id: str | None
    config_json: dict[str, Any] | None


@dataclass(slots=True, frozen=True)
class CalendarEventCandidate:
    """Canonical event candidate derived from one VEVENT."""

    source_external_id: str | None
    external_event_id: str | None
    type: str
    timestamp_start: datetime
    timestamp_end: datetime | None
    title: str | None
    summary: str | None
    raw_payload: dict[str, Any] | None
    derived_payload: dict[str, Any] | None


@dataclass(slots=True, frozen=True)
class CalendarTransformError:
    """Represents a non-fatal calendar document transform failure."""

    document: CalendarDocumentDescriptor
    message: str


@dataclass(slots=True, frozen=True)
class CalendarIngestionResult:
    """Summary of a completed calendar ingestion run."""

    run_id: int
    processed_document_count: int
    persisted_source_count: int
    persisted_event_count: int
    error_count: int
    status: str


__all__ = [
    "CalendarDocumentDescriptor",
    "CalendarEventCandidate",
    "CalendarIngestionResult",
    "CalendarParsedProperty",
    "CalendarSourceCandidate",
    "CalendarTransformError",
    "ParsedCalendarDocument",
    "ParsedCalendarEvent",
]
