"""Integration tests for calendar staged ingestion persistence and lifecycle."""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from pixelpast.ingestion.calendar import CalendarIngestionService
from pixelpast.persistence.models import Event, JobRun, Source
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import Settings


def test_calendar_ingestion_persists_sources_and_events_idempotently() -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    try:
        calendar_path = workspace_root / "work.ics"
        calendar_path.write_text(
            _build_calendar_document(
                external_id="cal-123",
                name="Work",
                events=(
                    (
                        "event-1",
                        "20240102T091500Z",
                        "20240102T101500Z",
                        "Standup",
                        "Planning",
                    ),
                    (
                        "event-2",
                        "20240103T120000Z",
                        "20240103T130000Z",
                        "Lunch",
                        "Food",
                    ),
                ),
            ),
            encoding="utf-8",
        )

        first_result = CalendarIngestionService().ingest(
            runtime=runtime,
            root=calendar_path,
        )
        with runtime.session_factory() as session:
            first_source = session.execute(select(Source)).scalar_one()
            first_events = list(
                session.execute(
                    select(Event).order_by(Event.timestamp_start, Event.id)
                ).scalars()
            )

        second_result = CalendarIngestionService().ingest(
            runtime=runtime,
            root=calendar_path,
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

        assert first_result.status == "completed"
        assert first_result.processed_document_count == 1
        assert first_result.persisted_source_count == 1
        assert first_result.persisted_event_count == 2

        assert second_result.status == "completed"
        assert second_result.processed_document_count == 1
        assert second_result.persisted_source_count == 1
        assert second_result.persisted_event_count == 2

        assert first_source.id == second_source.id
        assert [event.id for event in first_events] == [
            event.id for event in second_events
        ]
        assert [event.created_at for event in first_events] == [
            event.created_at for event in second_events
        ]

        assert len(job_runs) == 2
        assert job_runs[1].status == "completed"
        assert job_runs[1].progress_json == {
            "total": 1,
            "completed": 1,
            "inserted": 0,
            "updated": 0,
            "unchanged": 1,
            "skipped": 0,
            "failed": 0,
            "missing_from_source": 0,
            "persisted_event_count": 2,
        }
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_calendar_ingestion_replaces_events_for_existing_source_when_document_changes(
) -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    try:
        calendar_path = workspace_root / "work.ics"
        calendar_path.write_text(
            _build_calendar_document(
                external_id="cal-123",
                name="Work",
                events=(
                    (
                        "event-1",
                        "20240102T091500Z",
                        "20240102T101500Z",
                        "Standup",
                        "Planning",
                    ),
                ),
            ),
            encoding="utf-8",
        )

        CalendarIngestionService().ingest(runtime=runtime, root=calendar_path)
        with runtime.session_factory() as session:
            original_source = session.execute(select(Source)).scalar_one()
            original_events = list(
                session.execute(select(Event).order_by(Event.id)).scalars()
            )

        calendar_path.write_text(
            _build_calendar_document(
                external_id="cal-123",
                name="Work Calendar",
                events=(
                    (
                        "event-1",
                        "20240102T091500Z",
                        "20240102T111500Z",
                        "Standup Extended",
                        "Planning updated",
                    ),
                    (
                        "event-2",
                        "20240103T140000Z",
                        "20240103T150000Z",
                        "Review",
                        "Quarterly",
                    ),
                ),
            ),
            encoding="utf-8",
        )

        result = CalendarIngestionService().ingest(runtime=runtime, root=calendar_path)

        with runtime.session_factory() as session:
            source = session.execute(select(Source)).scalar_one()
            events = list(
                session.execute(
                    select(Event).order_by(Event.timestamp_start, Event.id)
                ).scalars()
            )
            latest_job_run = session.execute(
                select(JobRun).order_by(JobRun.id.desc())
            ).scalars().first()

        assert result.status == "completed"
        assert result.persisted_event_count == 2
        assert source.id == original_source.id
        assert source.name == "Work Calendar"
        assert [event.id for event in events] != [event.id for event in original_events]
        assert [event.title for event in events] == ["Standup Extended", "Review"]
        assert latest_job_run is not None
        assert latest_job_run.progress_json == {
            "total": 1,
            "completed": 1,
            "inserted": 0,
            "updated": 1,
            "unchanged": 0,
            "skipped": 0,
            "failed": 0,
            "missing_from_source": 0,
            "persisted_event_count": 2,
        }
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_calendar_ingestion_treats_duplicate_external_ids_as_partial_failure(
) -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    try:
        (workspace_root / "a-first.ics").write_text(
            _build_calendar_document(
                external_id="shared-cal",
                name="Work",
                events=(("event-1", "20240102T090000Z", None, "First", None),),
            ),
            encoding="utf-8",
        )
        (workspace_root / "b-second.ics").write_text(
            _build_calendar_document(
                external_id="shared-cal",
                name="Work Copy",
                events=(("event-2", "20240103T090000Z", None, "Second", None),),
            ),
            encoding="utf-8",
        )

        result = CalendarIngestionService().ingest(runtime=runtime, root=workspace_root)

        with runtime.session_factory() as session:
            source = session.execute(select(Source)).scalar_one()
            events = list(session.execute(select(Event).order_by(Event.id)).scalars())
            job_run = session.execute(
                select(JobRun).order_by(JobRun.id.desc())
            ).scalar_one()

        assert result.status == "partial_failure"
        assert result.processed_document_count == 1
        assert result.persisted_source_count == 1
        assert result.persisted_event_count == 1
        assert result.error_count == 1
        assert source.external_id == "shared-cal"
        assert source.name == "Work"
        assert [event.title for event in events] == ["First"]
        assert job_run.status == "partial_failure"
        assert job_run.progress_json == {
            "total": 1,
            "completed": 1,
            "inserted": 1,
            "updated": 0,
            "unchanged": 0,
            "skipped": 0,
            "failed": 1,
            "missing_from_source": 0,
            "persisted_event_count": 1,
        }
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def _create_runtime():
    runtime = create_runtime_context(settings=Settings(database_url="sqlite://"))
    initialize_database(runtime)
    return runtime


def _create_workspace_root() -> Path:
    workspace_root = Path("var") / f"calendar-ingest-{uuid4().hex}"
    workspace_root.mkdir(parents=True, exist_ok=False)
    return workspace_root


def _build_calendar_document(
    *,
    external_id: str,
    name: str,
    events: tuple[tuple[str, str, str | None, str | None, str | None], ...],
) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"X-WR-CALNAME:{name}",
        f"X-WR-RELCALID:{external_id}",
    ]
    for uid, starts_at, ends_at, summary, alt_description in events:
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTART:{starts_at}",
            ]
        )
        if ends_at is not None:
            lines.append(f"DTEND:{ends_at}")
        if summary is not None:
            lines.append(f"SUMMARY:{summary}")
        if alt_description is not None:
            lines.append(f"X-ALT-DESC:{alt_description}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\n".join(lines) + "\n"
