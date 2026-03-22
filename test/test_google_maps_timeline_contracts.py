"""Characterization tests for Google Maps Timeline contracts and fixtures."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pixelpast.ingestion.google_maps_timeline import (
    GoogleMapsTimelineDocumentCandidate,
    GoogleMapsTimelineDocumentDescriptor,
    GoogleMapsTimelineEventCandidate,
    GoogleMapsTimelineIngestionResult,
    GoogleMapsTimelineSourceCandidate,
    GoogleMapsTimelineTransformError,
    LoadedGoogleMapsTimelineExportDocument,
    ParsedGoogleMapsTimelineActivitySegment,
    ParsedGoogleMapsTimelineExport,
    ParsedGoogleMapsTimelinePathPoint,
    ParsedGoogleMapsTimelinePathSegment,
    ParsedGoogleMapsTimelineVisitSegment,
    build_google_maps_timeline_source_candidate,
    parse_google_maps_coordinate_pair,
    parse_google_maps_timeline_export_document,
    parse_google_maps_timeline_timestamp,
)
from pixelpast.ingestion.google_maps_timeline import contracts as google_maps_contracts


def test_google_maps_timeline_public_contract_imports_remain_stable() -> None:
    assert (
        GoogleMapsTimelineDocumentDescriptor
        is google_maps_contracts.GoogleMapsTimelineDocumentDescriptor
    )
    assert (
        LoadedGoogleMapsTimelineExportDocument
        is google_maps_contracts.LoadedGoogleMapsTimelineExportDocument
    )
    assert (
        ParsedGoogleMapsTimelineExport
        is google_maps_contracts.ParsedGoogleMapsTimelineExport
    )
    assert (
        ParsedGoogleMapsTimelineVisitSegment
        is google_maps_contracts.ParsedGoogleMapsTimelineVisitSegment
    )
    assert (
        ParsedGoogleMapsTimelinePathSegment
        is google_maps_contracts.ParsedGoogleMapsTimelinePathSegment
    )
    assert (
        ParsedGoogleMapsTimelinePathPoint
        is google_maps_contracts.ParsedGoogleMapsTimelinePathPoint
    )
    assert (
        ParsedGoogleMapsTimelineActivitySegment
        is google_maps_contracts.ParsedGoogleMapsTimelineActivitySegment
    )
    assert (
        GoogleMapsTimelineSourceCandidate
        is google_maps_contracts.GoogleMapsTimelineSourceCandidate
    )
    assert (
        GoogleMapsTimelineEventCandidate
        is google_maps_contracts.GoogleMapsTimelineEventCandidate
    )
    assert (
        GoogleMapsTimelineDocumentCandidate
        is google_maps_contracts.GoogleMapsTimelineDocumentCandidate
    )
    assert (
        GoogleMapsTimelineTransformError
        is google_maps_contracts.GoogleMapsTimelineTransformError
    )
    assert (
        GoogleMapsTimelineIngestionResult
        is google_maps_contracts.GoogleMapsTimelineIngestionResult
    )


def test_google_maps_timeline_fixture_characterizes_on_device_export_shape() -> None:
    fixture_path = Path("test/assets/googlemaps_timeline_test_fixture.json")

    parsed = parse_google_maps_timeline_export_document(
        descriptor=GoogleMapsTimelineDocumentDescriptor(path=fixture_path),
        text=fixture_path.read_text(encoding="utf-8"),
    )

    assert parsed.top_level_keys == (
        "semanticSegments",
        "rawSignals",
        "userLocationProfile",
    )
    assert parsed.semantic_segment_count == 3
    assert parsed.has_raw_signals is True
    assert parsed.raw_signal_count == 4
    assert parsed.has_user_location_profile is True
    assert len(parsed.visit_segments) == 1
    assert len(parsed.timeline_path_segments) == 1
    assert len(parsed.activity_segments) == 1

    visit = parsed.visit_segments[0]
    assert visit.segment_index == 0
    assert visit.start_time == datetime(2026, 1, 1, 6, 38, 37, tzinfo=UTC)
    assert visit.end_time == datetime(2026, 1, 1, 6, 45, 50, tzinfo=UTC)
    assert visit.start_time_timezone_utc_offset_minutes == 60
    assert visit.end_time_timezone_utc_offset_minutes == 60
    assert visit.hierarchy_level == 0
    assert visit.visit_probability == 0.36148369312286377
    assert visit.google_place_id == "djfFmwNTmXxKqVmG7"
    assert visit.semantic_type == "UNKNOWN"
    assert visit.candidate_probability == 0.3317331075668335
    assert visit.is_timeless_visit is None
    assert visit.latitude == 52.5252309
    assert visit.longitude == 13.368363

    timeline_path = parsed.timeline_path_segments[0]
    assert timeline_path.segment_index == 1
    assert timeline_path.start_time == datetime(2026, 1, 1, 17, 0, tzinfo=UTC)
    assert timeline_path.end_time == datetime(2026, 1, 1, 19, 0, tzinfo=UTC)
    assert len(timeline_path.points) == 3
    assert timeline_path.points[0].timestamp == datetime(
        2025,
        3,
        25,
        17,
        4,
        tzinfo=UTC,
    )
    assert timeline_path.points[0].latitude == 52.5252309
    assert timeline_path.points[0].longitude == 13.368363

    activity = parsed.activity_segments[0]
    assert activity.segment_index == 2
    assert activity.start_time == datetime(2026, 1, 1, 17, 37, 46, tzinfo=UTC)
    assert activity.end_time == datetime(2026, 1, 1, 17, 40, 6, tzinfo=UTC)
    assert activity.start_time_timezone_utc_offset_minutes == 60
    assert activity.end_time_timezone_utc_offset_minutes == 60
    assert activity.start_latitude == 52.5252309
    assert activity.start_longitude == 13.368363
    assert activity.end_latitude == 52.5252309
    assert activity.end_longitude == 13.368363
    assert activity.distance_meters == 107.74786376953125
    assert activity.activity_probability == 0.8913857936859131
    assert activity.google_activity_type == "WALKING"
    assert activity.top_candidate_probability == 0.46404823660850525


def test_google_maps_timeline_source_candidate_is_file_scoped() -> None:
    descriptor = GoogleMapsTimelineDocumentDescriptor(path=Path("fixture.json"))
    parsed = parse_google_maps_timeline_export_document(
        descriptor=descriptor,
        text=(
            "{"
            '"semanticSegments": [],'
            '"rawSignals": [],'
            '"userLocationProfile": {}'
            "}"
        ),
    )

    source_candidate = build_google_maps_timeline_source_candidate(parsed)

    assert source_candidate == GoogleMapsTimelineSourceCandidate(
        type="google_maps_timeline",
        name="fixture",
        external_id=f"google_maps_timeline:{descriptor.origin_label}",
        config_json={
            "origin_path": descriptor.origin_label,
            "export_format": "google_maps_timeline_on_device",
        },
    )


def test_google_maps_timeline_timestamp_parsing_normalizes_offsets_to_utc() -> None:
    assert parse_google_maps_timeline_timestamp("2026-01-01T07:38:37.000+01:00") == (
        datetime(2026, 1, 1, 6, 38, 37, tzinfo=UTC)
    )


def test_google_maps_timeline_coordinate_parsing_tolerates_degree_encoding_artifacts() -> (
    None
):
    assert parse_google_maps_coordinate_pair("52.5252309Â°, 13.3683630Â°") == (
        52.5252309,
        13.368363,
    )
    assert parse_google_maps_coordinate_pair("52.5252309Ã‚Â°, 13.3683630Ã‚Â°") == (
        52.5252309,
        13.368363,
    )


def test_google_maps_timeline_fixture_explicitly_captures_path_time_mismatch() -> None:
    fixture_path = Path("test/assets/googlemaps_timeline_test_fixture.json")
    parsed = parse_google_maps_timeline_export_document(
        descriptor=GoogleMapsTimelineDocumentDescriptor(path=fixture_path),
        text=fixture_path.read_text(encoding="utf-8"),
    )

    timeline_path = parsed.timeline_path_segments[0]
    activity = parsed.activity_segments[0]

    assert timeline_path.start_time.date().isoformat() == "2026-01-01"
    assert timeline_path.points[0].timestamp.date().isoformat() == "2025-03-25"
    assert activity.start_time.date().isoformat() == "2026-01-01"


def test_google_maps_timeline_parser_rejects_legacy_timeline_objects_exports() -> None:
    descriptor = GoogleMapsTimelineDocumentDescriptor(path=Path("legacy.json"))

    try:
        parse_google_maps_timeline_export_document(
            descriptor=descriptor,
            text='{"timelineObjects": []}',
        )
    except ValueError as error:
        assert str(error) == (
            "Google Maps Timeline export uses unsupported legacy 'timelineObjects' "
            f"format: {descriptor.origin_label}"
        )
    else:
        raise AssertionError("Expected legacy timelineObjects export to fail.")


def test_google_maps_timeline_parser_rejects_records_json_locations_exports() -> None:
    descriptor = GoogleMapsTimelineDocumentDescriptor(path=Path("records.json"))

    try:
        parse_google_maps_timeline_export_document(
            descriptor=descriptor,
            text='{"locations": []}',
        )
    except ValueError as error:
        assert str(error) == (
            "Google Maps Timeline export uses unsupported 'locations' format: "
            f"{descriptor.origin_label}"
        )
    else:
        raise AssertionError("Expected locations export to fail.")


def test_google_maps_timeline_parser_rejects_non_object_documents() -> None:
    descriptor = GoogleMapsTimelineDocumentDescriptor(path=Path("invalid.json"))

    try:
        parse_google_maps_timeline_export_document(
            descriptor=descriptor,
            text='[{"semanticSegments": []}]',
        )
    except ValueError as error:
        assert str(error) == (
            "Google Maps Timeline export must contain a top-level JSON object: "
            f"{descriptor.origin_label}"
        )
    else:
        raise AssertionError("Expected non-object export to fail.")
