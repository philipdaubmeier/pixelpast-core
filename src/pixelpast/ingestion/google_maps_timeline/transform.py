"""Google Maps Timeline parsing and source-candidate helpers."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any

from pixelpast.ingestion.google_maps_timeline.contracts import (
    GoogleMapsTimelineDocumentCandidate,
    GoogleMapsTimelineDocumentDescriptor,
    GoogleMapsTimelineEventCandidate,
    GoogleMapsTimelineSourceCandidate,
    LoadedGoogleMapsTimelineExportDocument,
    ParsedGoogleMapsTimelineActivitySegment,
    ParsedGoogleMapsTimelineExport,
    ParsedGoogleMapsTimelinePathPoint,
    ParsedGoogleMapsTimelinePathSegment,
    ParsedGoogleMapsTimelineVisitSegment,
)

_DEGREE_ARTIFACTS = ("Ã‚Â°", "Â°", "°")
_COORDINATE_PATTERN = re.compile(
    r"^\s*(?P<latitude>[-+]?\d+(?:\.\d+)?)\s*,\s*(?P<longitude>[-+]?\d+(?:\.\d+)?)\s*$"
)
_SEGMENT_METADATA_KEYS = {
    "startTime",
    "endTime",
    "startTimeTimezoneUtcOffsetMinutes",
    "endTimeTimezoneUtcOffsetMinutes",
}
_SUPPORTED_SEGMENT_KINDS = {"visit", "activity", "timelinePath"}


def parse_google_maps_timeline_export_document(
    *,
    descriptor: GoogleMapsTimelineDocumentDescriptor,
    text: str,
) -> ParsedGoogleMapsTimelineExport:
    """Parse one Google Maps Timeline export JSON object into explicit contracts."""

    return parse_loaded_google_maps_timeline_export_document(
        LoadedGoogleMapsTimelineExportDocument(descriptor=descriptor, text=text)
    )


def parse_loaded_google_maps_timeline_export_document(
    document: LoadedGoogleMapsTimelineExportDocument,
) -> ParsedGoogleMapsTimelineExport:
    """Parse one loaded Google Maps Timeline document into semantic segments."""

    try:
        payload = json.loads(document.text)
    except json.JSONDecodeError as error:
        raise ValueError(
            "Google Maps Timeline export is not valid JSON: "
            f"{document.descriptor.origin_label}"
        ) from error

    if not isinstance(payload, dict):
        raise ValueError(
            "Google Maps Timeline export must contain a top-level JSON object: "
            f"{document.descriptor.origin_label}"
        )
    if "timelineObjects" in payload:
        raise ValueError(
            "Google Maps Timeline export uses unsupported legacy 'timelineObjects' "
            f"format: {document.descriptor.origin_label}"
        )
    if "locations" in payload:
        raise ValueError(
            "Google Maps Timeline export uses unsupported 'locations' format: "
            f"{document.descriptor.origin_label}"
        )

    semantic_segments = payload.get("semanticSegments")
    if not isinstance(semantic_segments, list):
        raise ValueError(
            "Google Maps Timeline export must contain a top-level "
            f"'semanticSegments' array: {document.descriptor.origin_label}"
        )

    visits: list[ParsedGoogleMapsTimelineVisitSegment] = []
    timeline_paths: list[ParsedGoogleMapsTimelinePathSegment] = []
    activities: list[ParsedGoogleMapsTimelineActivitySegment] = []
    warning_messages: list[str] = []

    for segment_index, raw_segment in enumerate(semantic_segments):
        if not isinstance(raw_segment, dict):
            raise ValueError(
                "Google Maps Timeline semantic segment must be a JSON object at "
                f"index {segment_index}: {document.descriptor.origin_label}"
            )
        supported_kinds = sorted(
            key for key in raw_segment if key in _SUPPORTED_SEGMENT_KINDS
        )
        unsupported_kinds = sorted(
            key
            for key in raw_segment
            if key not in _SEGMENT_METADATA_KEYS and key not in _SUPPORTED_SEGMENT_KINDS
        )
        if not supported_kinds and unsupported_kinds:
            warning_messages.append(
                "Skipping unsupported Google Maps Timeline semantic segment kind(s) "
                f"{', '.join(unsupported_kinds)} at index {segment_index}: "
                f"{document.descriptor.origin_label}"
            )
            continue
        if "visit" in raw_segment:
            visits.append(
                _parse_visit_segment(raw_segment, segment_index=segment_index)
            )
        if "timelinePath" in raw_segment:
            timeline_paths.append(
                _parse_timeline_path_segment(raw_segment, segment_index=segment_index)
            )
        if "activity" in raw_segment:
            activities.append(
                _parse_activity_segment(raw_segment, segment_index=segment_index)
            )

    raw_signals = payload.get("rawSignals")
    raw_signal_count = len(raw_signals) if isinstance(raw_signals, list) else 0

    return ParsedGoogleMapsTimelineExport(
        descriptor=document.descriptor,
        top_level_keys=tuple(payload.keys()),
        semantic_segment_count=len(semantic_segments),
        raw_signal_count=raw_signal_count,
        has_raw_signals="rawSignals" in payload,
        has_user_location_profile="userLocationProfile" in payload,
        visit_segments=tuple(visits),
        timeline_path_segments=tuple(timeline_paths),
        activity_segments=tuple(activities),
        warning_messages=tuple(warning_messages),
    )


def build_google_maps_timeline_source_external_id(
    descriptor: GoogleMapsTimelineDocumentDescriptor,
) -> str:
    """Build the file-scoped canonical source external identifier."""

    return f"google_maps_timeline:{descriptor.origin_label}"


def build_google_maps_timeline_source_candidate(
    document: ParsedGoogleMapsTimelineExport,
) -> GoogleMapsTimelineSourceCandidate:
    """Build the canonical source candidate represented by one export document."""

    descriptor = document.descriptor
    return GoogleMapsTimelineSourceCandidate(
        type="google_maps_timeline",
        name=descriptor.path.stem,
        external_id=build_google_maps_timeline_source_external_id(descriptor),
        config_json={
            "origin_path": descriptor.origin_label,
            "export_format": "google_maps_timeline_on_device",
        },
    )


def build_google_maps_timeline_event_candidates(
    document: ParsedGoogleMapsTimelineExport,
) -> tuple[GoogleMapsTimelineEventCandidate, ...]:
    """Build canonical Google Maps Timeline event candidates for one document."""

    source_external_id = build_google_maps_timeline_source_external_id(
        document.descriptor
    )
    visit_candidates = _build_visit_event_candidates(
        document=document,
        source_external_id=source_external_id,
    )
    activity_candidates = _build_activity_event_candidates(
        document=document,
        source_external_id=source_external_id,
    )
    return tuple(
        sorted(
            [*visit_candidates, *activity_candidates],
            key=_google_maps_event_sort_key,
        )
    )


def build_google_maps_timeline_document_candidate(
    document: ParsedGoogleMapsTimelineExport,
) -> GoogleMapsTimelineDocumentCandidate:
    """Build one explicit document-level transform result."""

    return GoogleMapsTimelineDocumentCandidate(
        document=document.descriptor,
        source=build_google_maps_timeline_source_candidate(document),
        events=build_google_maps_timeline_event_candidates(document),
    )


def parse_google_maps_timeline_timestamp(value: object) -> datetime:
    """Parse one ISO 8601 timestamp and normalize it to UTC."""

    if not isinstance(value, str):
        raise ValueError("Google Maps Timeline timestamp must be a string.")

    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ValueError(
            f"Google Maps Timeline timestamp is not a valid ISO 8601 value: {value!r}"
        ) from error

    if parsed.tzinfo is None:
        raise ValueError(
            "Google Maps Timeline timestamp must include a timezone offset: "
            f"{value!r}"
        )

    return parsed.astimezone(UTC)


def parse_google_maps_coordinate_pair(value: object) -> tuple[float, float]:
    """Parse one Google Maps coordinate string into latitude and longitude."""

    if not isinstance(value, str):
        raise ValueError("Google Maps Timeline coordinates must be a string.")

    normalized = value.strip()
    for artifact in _DEGREE_ARTIFACTS:
        normalized = normalized.replace(artifact, "")

    match = _COORDINATE_PATTERN.match(normalized)
    if match is None:
        raise ValueError(
            "Google Maps Timeline coordinates must be '<lat>, <lng>': "
            f"{value!r}"
        )

    return (
        float(match.group("latitude")),
        float(match.group("longitude")),
    )


def _parse_visit_segment(
    raw_segment: dict[str, Any],
    *,
    segment_index: int,
) -> ParsedGoogleMapsTimelineVisitSegment:
    visit = _require_object(raw_segment.get("visit"), field_name="visit")
    top_candidate = _optional_object(visit.get("topCandidate"))
    place_location = (
        _optional_object(top_candidate.get("placeLocation"))
        if top_candidate
        else None
    )
    coordinates = (
        parse_google_maps_coordinate_pair(place_location["latLng"])
        if place_location is not None and "latLng" in place_location
        else (None, None)
    )

    return ParsedGoogleMapsTimelineVisitSegment(
        segment_index=segment_index,
        start_time=parse_google_maps_timeline_timestamp(raw_segment.get("startTime")),
        end_time=parse_google_maps_timeline_timestamp(raw_segment.get("endTime")),
        start_time_timezone_utc_offset_minutes=_optional_int(
            raw_segment.get("startTimeTimezoneUtcOffsetMinutes")
        ),
        end_time_timezone_utc_offset_minutes=_optional_int(
            raw_segment.get("endTimeTimezoneUtcOffsetMinutes")
        ),
        hierarchy_level=_optional_int(visit.get("hierarchyLevel")),
        visit_probability=_optional_float(visit.get("probability")),
        google_place_id=(
            _optional_string(top_candidate.get("placeId"))
            if top_candidate
            else None
        ),
        semantic_type=(
            _optional_string(top_candidate.get("semanticType"))
            if top_candidate
            else None
        ),
        candidate_probability=(
            _optional_float(top_candidate.get("probability")) if top_candidate else None
        ),
        is_timeless_visit=_optional_bool(visit.get("isTimelessVisit")),
        latitude=coordinates[0],
        longitude=coordinates[1],
        raw_payload=dict(raw_segment),
    )


def _parse_timeline_path_segment(
    raw_segment: dict[str, Any],
    *,
    segment_index: int,
) -> ParsedGoogleMapsTimelinePathSegment:
    raw_points = raw_segment.get("timelinePath")
    if not isinstance(raw_points, list):
        raise ValueError("Google Maps Timeline 'timelinePath' must be a JSON array.")

    points = []
    for point_index, raw_point in enumerate(raw_points):
        point = _require_object(raw_point, field_name="timelinePath[]")
        latitude, longitude = parse_google_maps_coordinate_pair(point.get("point"))
        points.append(
            ParsedGoogleMapsTimelinePathPoint(
                point_index=point_index,
                timestamp=parse_google_maps_timeline_timestamp(point.get("time")),
                latitude=latitude,
                longitude=longitude,
            )
        )

    return ParsedGoogleMapsTimelinePathSegment(
        segment_index=segment_index,
        start_time=parse_google_maps_timeline_timestamp(raw_segment.get("startTime")),
        end_time=parse_google_maps_timeline_timestamp(raw_segment.get("endTime")),
        points=tuple(points),
        raw_payload=dict(raw_segment),
    )


def _parse_activity_segment(
    raw_segment: dict[str, Any],
    *,
    segment_index: int,
) -> ParsedGoogleMapsTimelineActivitySegment:
    activity = _require_object(raw_segment.get("activity"), field_name="activity")
    top_candidate = _optional_object(activity.get("topCandidate"))
    start = _optional_object(activity.get("start"))
    end = _optional_object(activity.get("end"))
    start_coordinates = (
        parse_google_maps_coordinate_pair(start["latLng"])
        if start is not None and "latLng" in start
        else (None, None)
    )
    end_coordinates = (
        parse_google_maps_coordinate_pair(end["latLng"])
        if end is not None and "latLng" in end
        else (None, None)
    )

    return ParsedGoogleMapsTimelineActivitySegment(
        segment_index=segment_index,
        start_time=parse_google_maps_timeline_timestamp(raw_segment.get("startTime")),
        end_time=parse_google_maps_timeline_timestamp(raw_segment.get("endTime")),
        start_time_timezone_utc_offset_minutes=_optional_int(
            raw_segment.get("startTimeTimezoneUtcOffsetMinutes")
        ),
        end_time_timezone_utc_offset_minutes=_optional_int(
            raw_segment.get("endTimeTimezoneUtcOffsetMinutes")
        ),
        start_latitude=start_coordinates[0],
        start_longitude=start_coordinates[1],
        end_latitude=end_coordinates[0],
        end_longitude=end_coordinates[1],
        distance_meters=_optional_float(activity.get("distanceMeters")),
        activity_probability=_optional_float(activity.get("probability")),
        google_activity_type=(
            _optional_string(top_candidate.get("type")) if top_candidate else None
        ),
        top_candidate_probability=(
            _optional_float(top_candidate.get("probability")) if top_candidate else None
        ),
        raw_payload=dict(raw_segment),
    )


def _build_visit_event_candidates(
    *,
    document: ParsedGoogleMapsTimelineExport,
    source_external_id: str,
) -> tuple[GoogleMapsTimelineEventCandidate, ...]:
    visits_by_window: dict[
        tuple[datetime, datetime], list[ParsedGoogleMapsTimelineVisitSegment]
    ] = {}
    for visit in document.visit_segments:
        visits_by_window.setdefault((visit.start_time, visit.end_time), []).append(
            visit
        )

    candidates: list[GoogleMapsTimelineEventCandidate] = []
    for start_time, end_time in sorted(visits_by_window):
        resolved_visit = min(
            visits_by_window[(start_time, end_time)],
            key=_visit_resolution_sort_key,
        )
        candidates.append(
            GoogleMapsTimelineEventCandidate(
                source_external_id=source_external_id,
                external_event_id=_build_event_external_id(
                    segment_kind="visit",
                    start_time=resolved_visit.start_time,
                    end_time=resolved_visit.end_time,
                ),
                type="timeline_visit",
                timestamp_start=resolved_visit.start_time,
                timestamp_end=resolved_visit.end_time,
                title=_normalize_visit_title(resolved_visit.semantic_type),
                summary=None,
                latitude=resolved_visit.latitude,
                longitude=resolved_visit.longitude,
                raw_payload={
                    "segment_kind": "visit",
                    "googlePlaceId": resolved_visit.google_place_id,
                    "semanticType": resolved_visit.semantic_type,
                    "visitProbability": resolved_visit.visit_probability,
                    "candidateProbability": resolved_visit.candidate_probability,
                    "hierarchyLevel": resolved_visit.hierarchy_level,
                    "isTimelessVisit": resolved_visit.is_timeless_visit,
                },
                derived_payload=None,
            )
        )
    return tuple(candidates)


def _build_activity_event_candidates(
    *,
    document: ParsedGoogleMapsTimelineExport,
    source_external_id: str,
) -> tuple[GoogleMapsTimelineEventCandidate, ...]:
    candidates: list[GoogleMapsTimelineEventCandidate] = []
    for activity in sorted(document.activity_segments, key=_activity_sort_key):
        path_points = _build_reconciled_activity_path_points(
            activity=activity,
            timeline_paths=document.timeline_path_segments,
        )
        candidates.append(
            GoogleMapsTimelineEventCandidate(
                source_external_id=source_external_id,
                external_event_id=_build_event_external_id(
                    segment_kind="activity",
                    start_time=activity.start_time,
                    end_time=activity.end_time,
                ),
                type="timeline_activity",
                timestamp_start=activity.start_time,
                timestamp_end=activity.end_time,
                title=_normalize_activity_title(activity.google_activity_type),
                summary=None,
                latitude=activity.start_latitude,
                longitude=activity.start_longitude,
                raw_payload={
                    "segment_kind": "activity",
                    "googleActivityType": activity.google_activity_type,
                    "activityProbability": activity.activity_probability,
                    "topCandidateProbability": activity.top_candidate_probability,
                    "distanceMeters": activity.distance_meters,
                    "startLocation": _build_location_payload(
                        activity.start_latitude,
                        activity.start_longitude,
                    ),
                    "endLocation": _build_location_payload(
                        activity.end_latitude,
                        activity.end_longitude,
                    ),
                    "pathPoints": path_points,
                },
                derived_payload=None,
            )
        )
    return tuple(candidates)


def _build_reconciled_activity_path_points(
    *,
    activity: ParsedGoogleMapsTimelineActivitySegment,
    timeline_paths: tuple[ParsedGoogleMapsTimelinePathSegment, ...],
) -> list[dict[str, Any]]:
    sortable_points: list[tuple[datetime, int, int, float, float]] = []

    if activity.start_latitude is not None and activity.start_longitude is not None:
        sortable_points.append(
            (
                activity.start_time,
                -1,
                -1,
                activity.start_latitude,
                activity.start_longitude,
            )
        )

    for path_segment in timeline_paths:
        if not _time_windows_overlap(
            first_start=activity.start_time,
            first_end=activity.end_time,
            second_start=path_segment.start_time,
            second_end=path_segment.end_time,
        ):
            continue
        for point in path_segment.points:
            if (
                point.timestamp < activity.start_time
                or point.timestamp > activity.end_time
            ):
                continue
            sortable_points.append(
                (
                    point.timestamp,
                    path_segment.segment_index,
                    point.point_index,
                    point.latitude,
                    point.longitude,
                )
            )

    if activity.end_latitude is not None and activity.end_longitude is not None:
        sortable_points.append(
            (
                activity.end_time,
                max(
                    (path.segment_index for path in timeline_paths),
                    default=activity.segment_index,
                )
                + 1,
                0,
                activity.end_latitude,
                activity.end_longitude,
            )
        )

    sortable_points.sort()
    deduplicated_points: list[dict[str, Any]] = []
    seen_points: set[tuple[str, float, float]] = set()
    for timestamp, _, _, latitude, longitude in sortable_points:
        identity = (timestamp.isoformat(), latitude, longitude)
        if identity in seen_points:
            continue
        seen_points.add(identity)
        deduplicated_points.append(
            {
                "time": timestamp.isoformat(),
                "latitude": latitude,
                "longitude": longitude,
            }
        )
    return deduplicated_points


def _time_windows_overlap(
    *,
    first_start: datetime,
    first_end: datetime,
    second_start: datetime,
    second_end: datetime,
) -> bool:
    return first_start <= second_end and second_start <= first_end


def _visit_resolution_sort_key(
    visit: ParsedGoogleMapsTimelineVisitSegment,
) -> tuple[int, float, int]:
    hierarchy_level = (
        visit.hierarchy_level if visit.hierarchy_level is not None else 10**9
    )
    candidate_probability = (
        -visit.candidate_probability if visit.candidate_probability is not None else 1.0
    )
    return (hierarchy_level, candidate_probability, visit.segment_index)


def _activity_sort_key(
    activity: ParsedGoogleMapsTimelineActivitySegment,
) -> tuple[datetime, datetime, int]:
    return (activity.start_time, activity.end_time, activity.segment_index)


def _google_maps_event_sort_key(
    event: GoogleMapsTimelineEventCandidate,
) -> tuple[datetime, datetime, str, str]:
    timestamp_end = event.timestamp_end or event.timestamp_start
    return (
        event.timestamp_start,
        timestamp_end,
        event.type,
        event.external_event_id or "",
    )


def _normalize_visit_title(semantic_type: str | None) -> str:
    title = _normalize_label(semantic_type)
    if title is None or title.casefold() == "unknown":
        return "Visit"
    return title


def _normalize_activity_title(activity_type: str | None) -> str:
    title = _normalize_label(activity_type)
    if title is None or title.casefold() == "unknown":
        return "Movement"
    return title


def _normalize_label(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized.replace("_", " ").casefold().title()


def _build_location_payload(
    latitude: float | None,
    longitude: float | None,
) -> dict[str, float] | None:
    if latitude is None or longitude is None:
        return None
    return {
        "latitude": latitude,
        "longitude": longitude,
    }


def _build_event_external_id(
    *,
    segment_kind: str,
    start_time: datetime,
    end_time: datetime,
) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    digest.update(segment_kind.encode("utf-8"))
    digest.update(b"\x1f")
    digest.update(start_time.isoformat().encode("utf-8"))
    digest.update(b"\x1f")
    digest.update(end_time.isoformat().encode("utf-8"))
    return digest.hexdigest()


def _require_object(value: object, *, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Google Maps Timeline '{field_name}' must be a JSON object.")
    return value


def _optional_object(value: object) -> dict[str, Any] | None:
    if value is None:
        return None
    return _require_object(value, field_name="nested object")


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("Google Maps Timeline integer field must contain an integer.")
    return value


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Google Maps Timeline numeric field must contain a number.")
    return float(value)


def _optional_bool(value: object) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    raise ValueError("Google Maps Timeline boolean field must contain a boolean.")


__all__ = [
    "build_google_maps_timeline_document_candidate",
    "build_google_maps_timeline_event_candidates",
    "build_google_maps_timeline_source_candidate",
    "build_google_maps_timeline_source_external_id",
    "parse_google_maps_coordinate_pair",
    "parse_google_maps_timeline_export_document",
    "parse_google_maps_timeline_timestamp",
    "parse_loaded_google_maps_timeline_export_document",
]
