"""Public data contracts for Google Maps Timeline on-device ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True, frozen=True)
class GoogleMapsTimelineDocumentDescriptor:
    """One discovered Google Maps Timeline export document."""

    path: Path

    @property
    def origin_path(self) -> Path:
        """Return the normalized filesystem path for this document."""

        return self.path.expanduser().resolve()

    @property
    def origin_label(self) -> str:
        """Return the deterministic human-readable document identifier."""

        return self.origin_path.as_posix()


@dataclass(slots=True, frozen=True)
class LoadedGoogleMapsTimelineExportDocument:
    """Raw loaded text payload for one Google Maps Timeline export document."""

    descriptor: GoogleMapsTimelineDocumentDescriptor
    text: str


@dataclass(slots=True, frozen=True)
class ParsedGoogleMapsTimelinePathPoint:
    """One parsed path point from a timelinePath segment."""

    point_index: int
    timestamp: datetime
    latitude: float
    longitude: float


@dataclass(slots=True, frozen=True)
class ParsedGoogleMapsTimelineVisitSegment:
    """One parsed semantic visit segment prior to canonical transformation."""

    segment_index: int
    start_time: datetime
    end_time: datetime
    start_time_timezone_utc_offset_minutes: int | None
    end_time_timezone_utc_offset_minutes: int | None
    hierarchy_level: int | None
    visit_probability: float | None
    google_place_id: str | None
    semantic_type: str | None
    candidate_probability: float | None
    is_timeless_visit: bool | None
    latitude: float | None
    longitude: float | None
    raw_payload: dict[str, Any]


@dataclass(slots=True, frozen=True)
class ParsedGoogleMapsTimelinePathSegment:
    """One parsed semantic timelinePath segment prior to reconciliation."""

    segment_index: int
    start_time: datetime
    end_time: datetime
    points: tuple[ParsedGoogleMapsTimelinePathPoint, ...]
    raw_payload: dict[str, Any]


@dataclass(slots=True, frozen=True)
class ParsedGoogleMapsTimelineActivitySegment:
    """One parsed semantic activity segment prior to canonical transformation."""

    segment_index: int
    start_time: datetime
    end_time: datetime
    start_time_timezone_utc_offset_minutes: int | None
    end_time_timezone_utc_offset_minutes: int | None
    start_latitude: float | None
    start_longitude: float | None
    end_latitude: float | None
    end_longitude: float | None
    distance_meters: float | None
    activity_probability: float | None
    google_activity_type: str | None
    top_candidate_probability: float | None
    raw_payload: dict[str, Any]


@dataclass(slots=True, frozen=True)
class ParsedGoogleMapsTimelineExport:
    """Parsed Google Maps Timeline export payload and its semantic segments."""

    descriptor: GoogleMapsTimelineDocumentDescriptor
    top_level_keys: tuple[str, ...]
    semantic_segment_count: int
    raw_signal_count: int
    has_raw_signals: bool
    has_user_location_profile: bool
    visit_segments: tuple[ParsedGoogleMapsTimelineVisitSegment, ...]
    timeline_path_segments: tuple[ParsedGoogleMapsTimelinePathSegment, ...]
    activity_segments: tuple[ParsedGoogleMapsTimelineActivitySegment, ...]
    warning_messages: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class GoogleMapsTimelineSourceCandidate:
    """Canonical source candidate derived from one export document."""

    type: str
    name: str
    external_id: str
    config_json: dict[str, Any] | None


@dataclass(slots=True, frozen=True)
class GoogleMapsTimelineEventCandidate:
    """Canonical event candidate derived from one semantic segment."""

    source_external_id: str
    external_event_id: str | None
    type: str
    timestamp_start: datetime
    timestamp_end: datetime | None
    title: str | None
    summary: str | None
    latitude: float | None
    longitude: float | None
    raw_payload: dict[str, Any] | None
    derived_payload: dict[str, Any] | None


@dataclass(slots=True, frozen=True)
class GoogleMapsTimelineDocumentCandidate:
    """One transform result for a single export document."""

    document: GoogleMapsTimelineDocumentDescriptor
    source: GoogleMapsTimelineSourceCandidate
    events: tuple[GoogleMapsTimelineEventCandidate, ...]


@dataclass(slots=True, frozen=True)
class GoogleMapsTimelineTransformError:
    """Represents one non-fatal Google Maps Timeline transform failure."""

    document: GoogleMapsTimelineDocumentDescriptor
    message: str


@dataclass(slots=True, frozen=True)
class GoogleMapsTimelineIngestionResult:
    """Summary of a completed Google Maps Timeline ingestion run."""

    run_id: int
    processed_document_count: int
    persisted_source_count: int
    persisted_event_count: int
    error_count: int
    status: str


__all__ = [
    "GoogleMapsTimelineDocumentCandidate",
    "GoogleMapsTimelineDocumentDescriptor",
    "GoogleMapsTimelineEventCandidate",
    "GoogleMapsTimelineIngestionResult",
    "GoogleMapsTimelineSourceCandidate",
    "GoogleMapsTimelineTransformError",
    "LoadedGoogleMapsTimelineExportDocument",
    "ParsedGoogleMapsTimelineActivitySegment",
    "ParsedGoogleMapsTimelineExport",
    "ParsedGoogleMapsTimelinePathPoint",
    "ParsedGoogleMapsTimelinePathSegment",
    "ParsedGoogleMapsTimelineVisitSegment",
]
