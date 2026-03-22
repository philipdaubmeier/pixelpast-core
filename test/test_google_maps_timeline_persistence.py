"""Integration tests for Google Maps Timeline persistence and lifecycle seams."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from pixelpast.ingestion.google_maps_timeline import (
    GoogleMapsTimelineConnector,
    GoogleMapsTimelineDocumentLoadProgress,
    GoogleMapsTimelineIngestionPersistenceScope,
    GoogleMapsTimelineIngestionRunCoordinator,
    GoogleMapsTimelineStagedIngestionStrategy,
)
from pixelpast.ingestion.staged import StagedIngestionRunner
from pixelpast.persistence.models import Asset, Event, JobRun, Source
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import Settings


def test_google_maps_timeline_staged_ingestion_persists_source_and_events_idempotently(
) -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    try:
        export_path = workspace_root / "timeline-export.json"
        export_path.write_text(_build_google_maps_timeline_export(), encoding="utf-8")

        first_result, first_progress = _run_google_maps_timeline_ingestion(
            runtime=runtime,
            root=export_path,
        )
        with runtime.session_factory() as session:
            first_source = session.execute(select(Source)).scalar_one()
            first_events = list(
                session.execute(
                    select(Event).order_by(Event.timestamp_start, Event.id)
                ).scalars()
            )

        second_result, second_progress = _run_google_maps_timeline_ingestion(
            runtime=runtime,
            root=export_path,
        )
        with runtime.session_factory() as session:
            second_source = session.execute(select(Source)).scalar_one()
            second_events = list(
                session.execute(
                    select(Event).order_by(Event.timestamp_start, Event.id)
                ).scalars()
            )
            job_runs = list(
                session.execute(select(JobRun).order_by(JobRun.id)).scalars()
            )
            assets = list(session.execute(select(Asset)).scalars())

        assert first_result.status == "completed"
        assert first_result.processed_document_count == 1
        assert first_result.persisted_source_count == 1
        assert first_result.persisted_event_count == 2

        assert second_result.status == "completed"
        assert second_result.processed_document_count == 1
        assert second_result.persisted_source_count == 1
        assert second_result.persisted_event_count == 2

        assert first_source.id == second_source.id
        assert first_source.type == "google_maps_timeline"
        assert first_source.external_id == f"google_maps_timeline:{export_path.resolve().as_posix()}"
        assert first_source.config == {
            "origin_path": export_path.resolve().as_posix(),
            "export_format": "google_maps_timeline_on_device",
        }
        assert [event.id for event in first_events] == [event.id for event in second_events]
        assert [event.created_at for event in first_events] == [
            event.created_at for event in second_events
        ]
        assert [event.type for event in second_events] == [
            "timeline_visit",
            "timeline_activity",
        ]
        assert second_events[0].raw_payload["external_event_id"]
        assert second_events[1].raw_payload["external_event_id"]
        assert assets == []

        assert second_progress.persisted_outcomes == [
            "inserted=0;updated=0;unchanged=2;missing_from_source=0;skipped=0;persisted_event_count=2"
        ]
        assert second_progress.missing_from_source_count == 0
        assert len(job_runs) == 2
        assert job_runs[1].job == "google_maps_timeline"
    finally:
        runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_google_maps_timeline_staged_ingestion_updates_existing_events_by_external_identity(
) -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    try:
        export_path = workspace_root / "timeline-export.json"
        export_path.write_text(_build_google_maps_timeline_export(), encoding="utf-8")

        _run_google_maps_timeline_ingestion(runtime=runtime, root=export_path)
        with runtime.session_factory() as session:
            original_source = session.execute(select(Source)).scalar_one()
            original_events = list(
                session.execute(
                    select(Event).order_by(Event.timestamp_start, Event.id)
                ).scalars()
            )

        export_path.write_text(
            _build_google_maps_timeline_export(
                visit_semantic_type="WORK",
                activity_type="IN_PASSENGER_VEHICLE",
                activity_distance_meters=1800,
            ),
            encoding="utf-8",
        )

        result, progress = _run_google_maps_timeline_ingestion(
            runtime=runtime,
            root=export_path,
        )

        with runtime.session_factory() as session:
            source = session.execute(select(Source)).scalar_one()
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
        assert result.persisted_source_count == 1
        assert result.persisted_event_count == 2
        assert source.id == original_source.id
        assert [event.id for event in events] == [event.id for event in original_events]
        assert [event.title for event in events] == ["Work", "In Passenger Vehicle"]
        assert events[1].raw_payload["distanceMeters"] == 1800.0
        assert progress.persisted_outcomes == [
            "inserted=0;updated=2;unchanged=0;missing_from_source=0;skipped=0;persisted_event_count=2"
        ]
        assert latest_job_run is not None
        assert latest_job_run.job == "google_maps_timeline"
    finally:
        runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_google_maps_timeline_staged_ingestion_deletes_missing_visit_events() -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    try:
        export_path = workspace_root / "timeline-export.json"
        export_path.write_text(
            _build_google_maps_timeline_export(
                include_visit=True,
                include_activity=True,
            ),
            encoding="utf-8",
        )

        _run_google_maps_timeline_ingestion(runtime=runtime, root=export_path)

        export_path.write_text(
            _build_google_maps_timeline_export(
                include_visit=False,
                include_activity=True,
            ),
            encoding="utf-8",
        )
        result, progress = _run_google_maps_timeline_ingestion(
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
        assert result.persisted_event_count == 1
        assert [event.type for event in events] == ["timeline_activity"]
        assert progress.missing_from_source_count == 1
        assert progress.persisted_outcomes == [
            "inserted=0;updated=0;unchanged=1;missing_from_source=1;skipped=0;persisted_event_count=1"
        ]
    finally:
        runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_google_maps_timeline_staged_ingestion_deletes_missing_activity_events() -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    try:
        export_path = workspace_root / "timeline-export.json"
        export_path.write_text(
            _build_google_maps_timeline_export(
                include_visit=True,
                include_activity=True,
            ),
            encoding="utf-8",
        )

        _run_google_maps_timeline_ingestion(runtime=runtime, root=export_path)

        export_path.write_text(
            _build_google_maps_timeline_export(
                include_visit=True,
                include_activity=False,
            ),
            encoding="utf-8",
        )
        result, progress = _run_google_maps_timeline_ingestion(
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
        assert result.persisted_event_count == 1
        assert [event.type for event in events] == ["timeline_visit"]
        assert progress.missing_from_source_count == 1
        assert progress.persisted_outcomes == [
            "inserted=0;updated=0;unchanged=1;missing_from_source=1;skipped=0;persisted_event_count=1"
        ]
    finally:
        runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_google_maps_timeline_run_coordinator_persists_initial_job_run_state() -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    try:
        export_path = workspace_root / "timeline-export.json"
        export_path.write_text(_build_google_maps_timeline_export(), encoding="utf-8")

        run_id = GoogleMapsTimelineIngestionRunCoordinator().create_run(
            runtime=runtime,
            resolved_root=export_path.resolve(),
        )

        with runtime.session_factory() as session:
            job_run = session.execute(
                select(JobRun).where(JobRun.id == run_id)
            ).scalar_one()

        assert job_run.type == "ingest"
        assert job_run.job == "google_maps_timeline"
        assert job_run.mode == "full"
        assert job_run.phase == "initializing"
        assert job_run.status == "running"
        assert job_run.progress_json == {
            "total": None,
            "completed": 0,
            "inserted": 0,
            "updated": 0,
            "unchanged": 0,
            "skipped": 0,
            "failed": 0,
            "missing_from_source": 0,
            "root_path": export_path.resolve().as_posix(),
        }
    finally:
        runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def _run_google_maps_timeline_ingestion(
    *,
    runtime,
    root: Path,
):
    lifecycle = GoogleMapsTimelineIngestionRunCoordinator()
    run_id = lifecycle.create_run(runtime=runtime, resolved_root=root.resolve())
    progress = _FakeGoogleMapsTimelineProgress()
    runner = StagedIngestionRunner(
        strategy=GoogleMapsTimelineStagedIngestionStrategy(
            connector=GoogleMapsTimelineConnector()
        )
    )
    persistence = GoogleMapsTimelineIngestionPersistenceScope(
        runtime=runtime,
        lifecycle=lifecycle,
    )
    result = runner.run(
        resolved_root=root.resolve(),
        run_id=run_id,
        progress=progress,
        persistence=persistence,
    )
    return result, progress


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
    workspace_root = Path("var") / f"google-maps-ingest-{uuid4().hex}"
    workspace_root.mkdir(parents=True, exist_ok=False)
    return workspace_root


def _build_google_maps_timeline_export(
    *,
    visit_semantic_type: str = "HOME",
    activity_type: str = "WALKING",
    activity_distance_meters: int = 1200,
    include_visit: bool = True,
    include_activity: bool = True,
) -> str:
    semantic_segments: list[str] = []
    if include_visit:
        semantic_segments.append(
            f"""
    {{
      "startTime": "2026-01-02T08:00:00+01:00",
      "endTime": "2026-01-02T09:00:00+01:00",
      "visit": {{
        "hierarchyLevel": 0,
        "probability": 0.6,
        "topCandidate": {{
          "placeId": "place-low-level",
          "semanticType": "{visit_semantic_type}",
          "probability": 0.2,
          "placeLocation": {{
            "latLng": "52.5100, 13.4100"
          }}
        }}
      }}
    }}""".strip()
        )
    if include_activity:
        semantic_segments.append(
            f"""
    {{
      "startTime": "2026-01-02T08:00:00+01:00",
      "endTime": "2026-01-02T08:35:00+01:00",
      "activity": {{
        "probability": 0.95,
        "distanceMeters": {activity_distance_meters},
        "topCandidate": {{
          "type": "{activity_type}",
          "probability": 0.8
        }},
        "start": {{
          "latLng": "52.5200, 13.4200"
        }},
        "end": {{
          "latLng": "52.5300, 13.4300"
        }}
      }}
    }}""".strip()
        )
        semantic_segments.append(
            """
    {
      "startTime": "2026-01-02T07:50:00+01:00",
      "endTime": "2026-01-02T09:05:00+01:00",
      "timelinePath": [
        {
          "time": "2026-01-02T08:10:00+01:00",
          "point": "52.5210, 13.4210"
        },
        {
          "time": "2026-01-02T08:30:00+01:00",
          "point": "52.5300, 13.4300"
        }
      ]
    }""".strip()
        )

    return f"""
{{
  "semanticSegments": [
    {",\n    ".join(semantic_segments)}
  ],
  "rawSignals": [],
  "userLocationProfile": {{}}
}}
""".strip()


@dataclass
class _FakeGoogleMapsTimelineCounters:
    persisted_document_count: int = 0
    persisted_source_count: int = 0
    persisted_event_count: int = 0


class _FakeGoogleMapsTimelineProgress:
    def __init__(self) -> None:
        self.counters = _FakeGoogleMapsTimelineCounters()
        self.persisted_outcomes: list[str] = []
        self.missing_from_source_count = 0
        self.current_phase = "initializing"

    def start_phase(self, *, phase: str, total: int | None) -> None:
        del total
        self.current_phase = phase

    def finish_phase(self) -> None:
        return None

    def mark_discovered(self, *, path: str, discovered_file_count: int) -> None:
        del path, discovered_file_count

    def mark_missing_from_source(self, *, missing_from_source_count: int) -> None:
        self.missing_from_source_count = missing_from_source_count

    def mark_metadata_batch(
        self,
        progress: GoogleMapsTimelineDocumentLoadProgress,
    ) -> None:
        del progress

    def mark_analysis_success(self) -> None:
        return None

    def mark_analysis_failure(self, *, error) -> None:
        del error

    def mark_persisted(self, *, outcome: str) -> None:
        self.counters.persisted_document_count += 1
        self.counters.persisted_source_count += 1
        detailed_counts = {
            key: int(value)
            for key, value in (
                part.split("=", 1) for part in outcome.split(";") if part.strip()
            )
        }
        self.counters.persisted_event_count += detailed_counts["persisted_event_count"]
        self.persisted_outcomes.append(outcome)

    def finish_run(self, *, status: str) -> None:
        del status

    def fail_run(self) -> None:
        return None
