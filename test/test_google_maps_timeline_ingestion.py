"""Integration tests for Google Maps Timeline service-level ingestion behavior."""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from pixelpast.ingestion.google_maps_timeline import GoogleMapsTimelineIngestionService
from pixelpast.persistence.models import Asset, Event, JobRun, Source
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import Settings


def test_google_maps_timeline_ingestion_imports_checked_in_fixture_end_to_end() -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    fixture_path = Path("test/assets/googlemaps_timeline_test_fixture.json")
    export_path = workspace_root / "google-maps-timeline.json"
    export_path.write_text(fixture_path.read_text(encoding="utf-8"), encoding="utf-8")

    try:
        result = GoogleMapsTimelineIngestionService().ingest(
            runtime=runtime,
            root=export_path,
        )

        with runtime.session_factory() as session:
            sources = list(
                session.execute(select(Source).order_by(Source.id)).scalars()
            )
            events = list(
                session.execute(
                    select(Event).order_by(Event.timestamp_start, Event.id)
                ).scalars()
            )
            assets = list(session.execute(select(Asset).order_by(Asset.id)).scalars())
            job_run = (
                session.execute(select(JobRun).order_by(JobRun.id.desc()))
                .scalar_one()
            )

        assert result.status == "completed"
        assert result.processed_document_count == 1
        assert result.persisted_source_count == 1
        assert result.persisted_event_count == 2
        assert result.warning_messages == ()
        assert assets == []
        assert len(sources) == 1
        assert sources[0].type == "google_maps_timeline"
        assert sources[0].external_id == (
            f"google_maps_timeline:{export_path.resolve().as_posix()}"
        )
        assert [event.type for event in events] == [
            "timeline_visit",
            "timeline_activity",
        ]
        assert events[0].title == "Visit"
        assert events[1].title == "Walking"
        assert events[1].raw_payload["pathPoints"] == [
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
        ]
        assert job_run.job == "google_maps_timeline"
        assert job_run.status == "completed"
        assert job_run.progress_json == {
            "total": 1,
            "completed": 1,
            "inserted": 2,
            "updated": 0,
            "unchanged": 0,
            "skipped": 0,
            "failed": 0,
            "missing_from_source": 0,
            "persisted_event_count": 2,
        }
    finally:
        runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_google_maps_timeline_ingestion_clips_aligned_timeline_path_to_activity_window(
) -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    export_path = workspace_root / "aligned.json"
    export_path.write_text(
        _build_aligned_google_maps_timeline_export(),
        encoding="utf-8",
    )

    try:
        result = GoogleMapsTimelineIngestionService().ingest(
            runtime=runtime,
            root=export_path,
        )

        with runtime.session_factory() as session:
            events = list(
                session.execute(
                    select(Event).order_by(Event.timestamp_start, Event.id)
                ).scalars()
            )

        assert result.status == "completed"
        assert result.persisted_event_count == 3
        assert [event.title for event in events] == [
            "Home",
            "In Passenger Vehicle",
            "Walking",
        ]
        assert events[0].raw_payload["hierarchyLevel"] == 0
        assert events[1].raw_payload["pathPoints"] == [
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
        assert events[2].raw_payload["pathPoints"] == [
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
    finally:
        runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_google_maps_timeline_ingestion_is_idempotent_for_unchanged_export() -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    export_path = workspace_root / "timeline-export.json"
    export_path.write_text(
        _build_aligned_google_maps_timeline_export(),
        encoding="utf-8",
    )

    try:
        first_result = GoogleMapsTimelineIngestionService().ingest(
            runtime=runtime,
            root=export_path,
        )
        with runtime.session_factory() as session:
            first_events = list(
                session.execute(
                    select(Event).order_by(Event.timestamp_start, Event.id)
                ).scalars()
            )

        second_result = GoogleMapsTimelineIngestionService().ingest(
            runtime=runtime,
            root=export_path,
        )
        with runtime.session_factory() as session:
            second_events = list(
                session.execute(
                    select(Event).order_by(Event.timestamp_start, Event.id)
                ).scalars()
            )
            latest_job_run = (
                session.execute(select(JobRun).order_by(JobRun.id.desc()))
                .scalars()
                .first()
        )

        assert first_result.status == "completed"
        assert second_result.status == "completed"
        assert [event.id for event in first_events] == [
            event.id for event in second_events
        ]
        assert [event.created_at for event in first_events] == [
            event.created_at for event in second_events
        ]
        assert latest_job_run is not None
        assert latest_job_run.progress_json == {
            "total": 1,
            "completed": 1,
            "inserted": 0,
            "updated": 0,
            "unchanged": 3,
            "skipped": 0,
            "failed": 0,
            "missing_from_source": 0,
            "persisted_event_count": 3,
        }
    finally:
        runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_google_maps_timeline_ingestion_deletes_removed_visit_on_repeated_import(
) -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    export_path = workspace_root / "timeline-export.json"
    export_path.write_text(
        _build_aligned_google_maps_timeline_export(),
        encoding="utf-8",
    )

    try:
        GoogleMapsTimelineIngestionService().ingest(runtime=runtime, root=export_path)
        export_path.write_text(
            _build_aligned_google_maps_timeline_export(include_visit=False),
            encoding="utf-8",
        )

        result = GoogleMapsTimelineIngestionService().ingest(
            runtime=runtime,
            root=export_path,
        )

        with runtime.session_factory() as session:
            events = list(
                session.execute(
                    select(Event).order_by(Event.timestamp_start, Event.id)
                ).scalars()
            )
            latest_job_run = (
                session.execute(select(JobRun).order_by(JobRun.id.desc()))
                .scalars()
                .first()
            )

        assert result.status == "completed"
        assert [event.type for event in events] == [
            "timeline_activity",
            "timeline_activity",
        ]
        assert latest_job_run is not None
        assert latest_job_run.progress_json["missing_from_source"] == 1
    finally:
        runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_google_maps_timeline_ingestion_deletes_removed_activity_on_repeated_import(
) -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    export_path = workspace_root / "timeline-export.json"
    export_path.write_text(
        _build_aligned_google_maps_timeline_export(),
        encoding="utf-8",
    )

    try:
        GoogleMapsTimelineIngestionService().ingest(runtime=runtime, root=export_path)
        export_path.write_text(
            _build_aligned_google_maps_timeline_export(include_walking_activity=False),
            encoding="utf-8",
        )

        result = GoogleMapsTimelineIngestionService().ingest(
            runtime=runtime,
            root=export_path,
        )

        with runtime.session_factory() as session:
            events = list(
                session.execute(
                    select(Event).order_by(Event.timestamp_start, Event.id)
                ).scalars()
            )
            latest_job_run = (
                session.execute(select(JobRun).order_by(JobRun.id.desc()))
                .scalars()
                .first()
            )

        assert result.status == "completed"
        assert [event.title for event in events] == ["Home", "In Passenger Vehicle"]
        assert latest_job_run is not None
        assert latest_job_run.progress_json["missing_from_source"] == 1
    finally:
        runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_google_maps_timeline_ingestion_emits_shared_progress_snapshots() -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    export_path = workspace_root / "timeline-export.json"
    export_path.write_text(
        _build_aligned_google_maps_timeline_export(),
        encoding="utf-8",
    )
    snapshots = []

    try:
        result = GoogleMapsTimelineIngestionService().ingest(
            runtime=runtime,
            root=export_path,
            progress_callback=snapshots.append,
        )

        assert result.status == "completed"
        assert [
            snapshot.phase
            for snapshot in snapshots
            if snapshot.event == "phase_started"
        ] == [
            "filesystem discovery",
            "metadata extraction",
            "canonical persistence",
            "finalization",
        ]
        assert any(
            snapshot.event == "progress"
            and snapshot.phase == "canonical persistence"
            and snapshot.completed == 1
            and snapshot.inserted == 3
            and snapshot.total == 1
            for snapshot in snapshots
        )
        assert snapshots[-1].event == "run_finished"
        assert snapshots[-1].missing_from_source == 0
    finally:
        runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_google_maps_timeline_ingestion_rejects_legacy_old_format_exports() -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    export_path = workspace_root / "timelineObjects.json"
    export_path.write_text('{"timelineObjects": []}', encoding="utf-8")

    try:
        try:
            GoogleMapsTimelineIngestionService().ingest(
                runtime=runtime,
                root=export_path,
            )
        except ValueError as error:
            assert str(error) == (
                "Google Maps Timeline export uses unsupported legacy "
                "'timelineObjects' format: "
                f"{export_path.resolve().as_posix()}"
            )
        else:
            raise AssertionError("Expected legacy Google Maps export to fail.")

        with runtime.session_factory() as session:
            job_run = (
                session.execute(select(JobRun).order_by(JobRun.id.desc()))
                .scalar_one()
            )
            events = list(session.execute(select(Event)).scalars())
            sources = list(session.execute(select(Source)).scalars())

        assert job_run.status == "partial_failure"
        assert job_run.progress_json == {
            "total": 1,
            "completed": 1,
            "inserted": 0,
            "updated": 0,
            "unchanged": 0,
            "skipped": 0,
            "failed": 1,
            "missing_from_source": 0,
            "persisted_event_count": 0,
        }
        assert events == []
        assert sources == []
    finally:
        runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def _create_runtime(*, google_maps_timeline_root: Path | None = None):
    runtime = create_runtime_context(
        settings=Settings(
            database_url="sqlite://",
            google_maps_timeline_root=google_maps_timeline_root,
        )
    )
    initialize_database(runtime)
    return runtime


def _create_workspace_root() -> Path:
    workspace_root = Path("var") / f"google-maps-service-{uuid4().hex}"
    workspace_root.mkdir(parents=True, exist_ok=False)
    return workspace_root


def _build_aligned_google_maps_timeline_export(
    *,
    include_visit: bool = True,
    include_vehicle_activity: bool = True,
    include_walking_activity: bool = True,
) -> str:
    segments: list[str] = []
    if include_visit:
        segments.extend(
            [
                """
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
                        "latLng": "52.5000, 13.4000"
                      }
                    }
                  }
                }
                """.strip(),
                """
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
                        "latLng": "52.5100, 13.4100"
                      }
                    }
                  }
                }
                """.strip(),
            ]
        )
    if include_vehicle_activity:
        segments.append(
            """
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
                  "latLng": "52.5200, 13.4200"
                },
                "end": {
                  "latLng": "52.5300, 13.4300"
                }
              }
            }
            """.strip()
        )
    if include_walking_activity:
        segments.append(
            """
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
                  "latLng": "52.5300, 13.4300"
                },
                "end": {
                  "latLng": "52.5400, 13.4400"
                }
              }
            }
            """.strip()
        )
    if include_vehicle_activity or include_walking_activity:
        segments.append(
            """
            {
              "startTime": "2026-01-02T07:50:00+01:00",
              "endTime": "2026-01-02T09:05:00+01:00",
              "timelinePath": [
                {
                  "time": "2026-01-02T07:58:00+01:00",
                  "point": "52.5190, 13.4190"
                },
                {
                  "time": "2026-01-02T08:10:00+01:00",
                  "point": "52.5210, 13.4210"
                },
                {
                  "time": "2026-01-02T08:30:00+01:00",
                  "point": "52.5300, 13.4300"
                },
                {
                  "time": "2026-01-02T08:40:00+01:00",
                  "point": "52.5350, 13.4350"
                },
                {
                  "time": "2026-01-02T09:01:00+01:00",
                  "point": "52.5450, 13.4450"
                }
              ]
            }
            """.strip()
        )

    return (
        "{\n"
        '  "semanticSegments": [\n    '
        + ",\n    ".join(segments)
        + '\n  ],\n  "rawSignals": [],\n  "userLocationProfile": {}\n}'
    )
