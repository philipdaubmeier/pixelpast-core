"""Google Maps Timeline parsing and source-candidate helpers."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

from pixelpast.ingestion.google_maps_timeline.contracts import (
    GoogleMapsTimelineDocumentDescriptor,
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

    for segment_index, raw_segment in enumerate(semantic_segments):
        if not isinstance(raw_segment, dict):
            raise ValueError(
                "Google Maps Timeline semantic segment must be a JSON object at "
                f"index {segment_index}: {document.descriptor.origin_label}"
            )
        if "visit" in raw_segment:
            visits.append(_parse_visit_segment(raw_segment, segment_index=segment_index))
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
    place_location = _optional_object(top_candidate.get("placeLocation")) if top_candidate else None
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
        google_place_id=_optional_string(top_candidate.get("placeId")) if top_candidate else None,
        semantic_type=_optional_string(top_candidate.get("semanticType")) if top_candidate else None,
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
    "build_google_maps_timeline_source_candidate",
    "build_google_maps_timeline_source_external_id",
    "parse_google_maps_coordinate_pair",
    "parse_google_maps_timeline_export_document",
    "parse_google_maps_timeline_timestamp",
    "parse_loaded_google_maps_timeline_export_document",
]
