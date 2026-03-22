"""Characterization tests for Google Maps Timeline contracts and fixtures."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pixelpast.ingestion.google_maps_timeline import (
    build_google_maps_timeline_document_candidate,
    build_google_maps_timeline_event_candidates,
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
    assert parsed.warning_messages == ()

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


def test_google_maps_timeline_document_candidate_builds_visit_and_activity_events() -> None:
    fixture_path = Path("test/assets/googlemaps_timeline_test_fixture.json")
    parsed = parse_google_maps_timeline_export_document(
        descriptor=GoogleMapsTimelineDocumentDescriptor(path=fixture_path),
        text=fixture_path.read_text(encoding="utf-8"),
    )

    document_candidate = build_google_maps_timeline_document_candidate(parsed)

    assert document_candidate.document == GoogleMapsTimelineDocumentDescriptor(
        path=fixture_path
    )
    assert document_candidate.source.external_id == (
        f"google_maps_timeline:{fixture_path.resolve().as_posix()}"
    )
    assert len(document_candidate.events) == 2

    visit_event = next(
        event for event in document_candidate.events if event.type == "timeline_visit"
    )
    activity_event = next(
        event for event in document_candidate.events if event.type == "timeline_activity"
    )

    assert visit_event.title == "Visit"
    assert visit_event.latitude == 52.5252309
    assert visit_event.longitude == 13.368363
    assert visit_event.raw_payload == {
        "segment_kind": "visit",
        "googlePlaceId": "djfFmwNTmXxKqVmG7",
        "semanticType": "UNKNOWN",
        "visitProbability": 0.36148369312286377,
        "candidateProbability": 0.3317331075668335,
        "hierarchyLevel": 0,
        "isTimelessVisit": None,
    }

    assert activity_event.title == "Walking"
    assert activity_event.latitude == 52.5252309
    assert activity_event.longitude == 13.368363
    assert activity_event.raw_payload == {
        "segment_kind": "activity",
        "googleActivityType": "WALKING",
        "activityProbability": 0.8913857936859131,
        "topCandidateProbability": 0.46404823660850525,
        "distanceMeters": 107.74786376953125,
        "startLocation": {"latitude": 52.5252309, "longitude": 13.368363},
        "endLocation": {"latitude": 52.5252309, "longitude": 13.368363},
        "pathPoints": [
            {
                "time": "2026-01-01T17:37:46+00:00",
                "latitude": 52.5252309,
                "longitude": 13.368363,
            },
            {
                "time": "2026-01-01T17:40:06+00:00",
                "latitude": 52.5252309,
                "longitude": 13.368363,
            },
        ],
    }


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


def test_google_maps_timeline_transform_normalizes_duplicate_visits_and_reconciles_paths(
) -> None:
    descriptor = GoogleMapsTimelineDocumentDescriptor(path=Path("synthetic.json"))
    parsed = parse_google_maps_timeline_export_document(
        descriptor=descriptor,
        text="""
        {
          "semanticSegments": [
            {
              "startTime": "2026-01-02T08:00:00+01:00",
              "endTime": "2026-01-02T09:00:00+01:00",
              "visit": {
                "hierarchyLevel": 2,
                "probability": 0.4,
                "topCandidate": {
                  "placeId": "place-high-level",
                  "semanticType": "HOME",
                  "probability": 0.7,
                  "placeLocation": {
                    "latLng": "52.5000°, 13.4000°"
                  }
                }
              }
            },
            {
              "startTime": "2026-01-02T08:00:00+01:00",
              "endTime": "2026-01-02T09:00:00+01:00",
              "visit": {
                "hierarchyLevel": 0,
                "probability": 0.6,
                "topCandidate": {
                  "placeId": "place-low-level",
                  "semanticType": "HOME",
                  "probability": 0.2,
                  "placeLocation": {
                    "latLng": "52.5100°, 13.4100°"
                  }
                }
              }
            },
            {
              "startTime": "2026-01-02T08:00:00+01:00",
              "endTime": "2026-01-02T08:35:00+01:00",
              "activity": {
                "probability": 0.95,
                "distanceMeters": 1200,
                "topCandidate": {
                  "type": "IN_PASSENGER_VEHICLE",
                  "probability": 0.8
                },
                "start": {
                  "latLng": "52.5200°, 13.4200°"
                },
                "end": {
                  "latLng": "52.5300°, 13.4300°"
                }
              }
            },
            {
              "startTime": "2026-01-02T08:30:00+01:00",
              "endTime": "2026-01-02T09:00:00+01:00",
              "activity": {
                "probability": 0.75,
                "distanceMeters": 900,
                "topCandidate": {
                  "type": "WALKING",
                  "probability": 0.6
                },
                "start": {
                  "latLng": "52.5300°, 13.4300°"
                },
                "end": {
                  "latLng": "52.5400°, 13.4400°"
                }
              }
            },
            {
              "startTime": "2026-01-02T07:50:00+01:00",
              "endTime": "2026-01-02T09:05:00+01:00",
              "timelinePath": [
                {
                  "time": "2026-01-02T07:58:00+01:00",
                  "point": "52.5190°, 13.4190°"
                },
                {
                  "time": "2026-01-02T08:10:00+01:00",
                  "point": "52.5210°, 13.4210°"
                },
                {
                  "time": "2026-01-02T08:30:00+01:00",
                  "point": "52.5300°, 13.4300°"
                },
                {
                  "time": "2026-01-02T08:30:00+01:00",
                  "point": "52.5300°, 13.4300°"
                },
                {
                  "time": "2026-01-02T08:40:00+01:00",
                  "point": "52.5350°, 13.4350°"
                },
                {
                  "time": "2026-01-02T09:01:00+01:00",
                  "point": "52.5450°, 13.4450°"
                }
              ]
            },
            {
              "startTime": "2026-01-02T10:00:00+01:00",
              "endTime": "2026-01-02T10:10:00+01:00",
              "activity": {
                "probability": 0.55,
                "distanceMeters": 100,
                "topCandidate": {
                  "type": "RUNNING",
                  "probability": 0.5
                },
                "start": {
                  "latLng": "52.5500°, 13.4500°"
                },
                "end": {
                  "latLng": "52.5600°, 13.4600°"
                }
              }
            }
          ],
          "rawSignals": [],
          "userLocationProfile": {}
        }
        """,
    )

    candidates = build_google_maps_timeline_event_candidates(parsed)

    assert len(candidates) == 4

    visit_event = next(event for event in candidates if event.type == "timeline_visit")
    assert visit_event.title == "Home"
    assert visit_event.latitude == 52.51
    assert visit_event.longitude == 13.41
    assert visit_event.raw_payload["googlePlaceId"] == "place-low-level"
    assert visit_event.raw_payload["hierarchyLevel"] == 0

    vehicle_event = next(
        event
        for event in candidates
        if event.type == "timeline_activity" and event.title == "In Passenger Vehicle"
    )
    assert vehicle_event.raw_payload["pathPoints"] == [
        {
            "time": "2026-01-02T07:00:00+00:00",
            "latitude": 52.52,
            "longitude": 13.42,
        },
        {
            "time": "2026-01-02T07:10:00+00:00",
            "latitude": 52.521,
            "longitude": 13.421,
        },
        {
            "time": "2026-01-02T07:30:00+00:00",
            "latitude": 52.53,
            "longitude": 13.43,
        },
        {
            "time": "2026-01-02T07:35:00+00:00",
            "latitude": 52.53,
            "longitude": 13.43,
        },
    ]

    walking_event = next(
        event
        for event in candidates
        if event.type == "timeline_activity" and event.title == "Walking"
    )
    assert walking_event.raw_payload["pathPoints"] == [
        {
            "time": "2026-01-02T07:30:00+00:00",
            "latitude": 52.53,
            "longitude": 13.43,
        },
        {
            "time": "2026-01-02T07:40:00+00:00",
            "latitude": 52.535,
            "longitude": 13.435,
        },
        {
            "time": "2026-01-02T08:00:00+00:00",
            "latitude": 52.54,
            "longitude": 13.44,
        },
    ]

    running_event = next(
        event
        for event in candidates
        if event.type == "timeline_activity" and event.title == "Running"
    )
    assert running_event.raw_payload["pathPoints"] == [
        {
            "time": "2026-01-02T09:00:00+00:00",
            "latitude": 52.55,
            "longitude": 13.45,
        },
        {
            "time": "2026-01-02T09:10:00+00:00",
            "latitude": 52.56,
            "longitude": 13.46,
        },
    ]


def test_google_maps_timeline_parser_skips_unsupported_segment_kinds_with_warning(
) -> None:
    descriptor = GoogleMapsTimelineDocumentDescriptor(path=Path("unsupported.json"))

    parsed = parse_google_maps_timeline_export_document(
        descriptor=descriptor,
        text="""
        {
          "semanticSegments": [
            {
              "startTime": "2026-01-02T08:00:00+01:00",
              "endTime": "2026-01-02T08:10:00+01:00",
              "timelineMemory": {
                "id": "mem-1"
              }
            }
          ]
        }
        """,
    )

    assert parsed.visit_segments == ()
    assert parsed.timeline_path_segments == ()
    assert parsed.activity_segments == ()
    assert parsed.warning_messages == (
        "Skipping unsupported Google Maps Timeline semantic segment kind(s) "
        f"timelineMemory at index 0: {descriptor.origin_label}",
    )
