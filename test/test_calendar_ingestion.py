"""Integration tests for calendar staged ingestion persistence and lifecycle."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from pixelpast.ingestion.calendar import CalendarIngestionService
from pixelpast.persistence.models import Asset, Event, JobRun, Source
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
            "unchanged": 2,
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
            "inserted": 2,
            "updated": 0,
            "unchanged": 0,
            "skipped": 0,
            "failed": 0,
            "missing_from_source": 1,
            "persisted_event_count": 2,
        }
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_calendar_ingestion_deletes_events_missing_from_existing_source() -> None:
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

        CalendarIngestionService().ingest(runtime=runtime, root=calendar_path)
        with runtime.session_factory() as session:
            original_events = list(
                session.execute(
                    select(Event).order_by(Event.timestamp_start, Event.id)
                ).scalars()
            )

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

        result = CalendarIngestionService().ingest(runtime=runtime, root=calendar_path)

        with runtime.session_factory() as session:
            events = list(
                session.execute(
                    select(Event).order_by(Event.timestamp_start, Event.id)
                ).scalars()
            )
            latest_job_run = session.execute(
                select(JobRun).order_by(JobRun.id.desc())
            ).scalars().first()

        assert result.status == "completed"
        assert result.persisted_event_count == 1
        assert [event.title for event in events] == ["Standup"]
        assert [event.id for event in events] == [original_events[0].id]
        assert latest_job_run is not None
        assert latest_job_run.progress_json == {
            "total": 1,
            "completed": 1,
            "inserted": 0,
            "updated": 0,
            "unchanged": 1,
            "skipped": 0,
            "failed": 0,
            "missing_from_source": 1,
            "persisted_event_count": 1,
        }
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_calendar_ingestion_reconciles_missing_events_when_uids_repeat() -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    try:
        calendar_path = workspace_root / "series.ics"
        calendar_path.write_text(
            _build_calendar_document(
                external_id="cal-recurring",
                name="Series",
                events=(
                    (
                        "series-1",
                        "20240102T091500Z",
                        "20240102T101500Z",
                        "Occurrence One",
                        None,
                    ),
                    (
                        "series-1",
                        "20240103T091500Z",
                        "20240103T101500Z",
                        "Occurrence Two",
                        None,
                    ),
                ),
            ),
            encoding="utf-8",
        )

        CalendarIngestionService().ingest(runtime=runtime, root=calendar_path)

        calendar_path.write_text(
            _build_calendar_document(
                external_id="cal-recurring",
                name="Series",
                events=(
                    (
                        "series-1",
                        "20240102T091500Z",
                        "20240102T101500Z",
                        "Occurrence One",
                        None,
                    ),
                ),
            ),
            encoding="utf-8",
        )

        CalendarIngestionService().ingest(runtime=runtime, root=calendar_path)

        with runtime.session_factory() as session:
            events = list(
                session.execute(
                    select(Event).order_by(Event.timestamp_start, Event.id)
                ).scalars()
            )
            latest_job_run = session.execute(
                select(JobRun).order_by(JobRun.id.desc())
            ).scalars().first()

        assert [event.title for event in events] == ["Occurrence One"]
        assert latest_job_run is not None
        assert latest_job_run.progress_json == {
            "total": 1,
            "completed": 1,
            "inserted": 0,
            "updated": 0,
            "unchanged": 1,
            "skipped": 0,
            "failed": 0,
            "missing_from_source": 1,
            "persisted_event_count": 1,
        }
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_calendar_ingestion_updates_event_when_summary_changes_for_repeated_uid() -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    try:
        calendar_path = workspace_root / "series-update.ics"
        calendar_path.write_text(
            _build_calendar_document(
                external_id="cal-repeated-update",
                name="Series",
                events=(
                    (
                        "series-1",
                        "20240102T091500Z",
                        "20240102T101500Z",
                        "Occurrence One",
                        None,
                    ),
                    (
                        "series-1",
                        "20240103T091500Z",
                        "20240103T101500Z",
                        "Occurrence Two",
                        None,
                    ),
                ),
            ),
            encoding="utf-8",
        )

        CalendarIngestionService().ingest(runtime=runtime, root=calendar_path)

        calendar_path.write_text(
            _build_calendar_document(
                external_id="cal-repeated-update",
                name="Series",
                events=(
                    (
                        "series-1",
                        "20240102T091500Z",
                        "20240102T101500Z",
                        "Occurrence One Renamed",
                        None,
                    ),
                    (
                        "series-1",
                        "20240103T091500Z",
                        "20240103T101500Z",
                        "Occurrence Two",
                        None,
                    ),
                ),
            ),
            encoding="utf-8",
        )

        CalendarIngestionService().ingest(runtime=runtime, root=calendar_path)

        with runtime.session_factory() as session:
            events = list(
                session.execute(
                    select(Event).order_by(Event.timestamp_start, Event.id)
                ).scalars()
            )
            latest_job_run = session.execute(
                select(JobRun).order_by(JobRun.id.desc())
            ).scalars().first()

        assert [event.title for event in events] == [
            "Occurrence One Renamed",
            "Occurrence Two",
        ]
        assert latest_job_run is not None
        assert latest_job_run.progress_json == {
            "total": 1,
            "completed": 1,
            "inserted": 1,
            "updated": 0,
            "unchanged": 1,
            "skipped": 0,
            "failed": 0,
            "missing_from_source": 1,
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


def test_calendar_ingestion_reads_zip_backed_fixture_without_creating_assets() -> None:
    fixture_path = Path("test") / "assets" / "outlook_cal_export_test_fixture.ics"
    workspace_root = _create_workspace_root()
    archive_path = workspace_root / "calendar-export.zip"
    runtime = _create_runtime(calendar_root=archive_path)
    try:
        with zipfile.ZipFile(archive_path, mode="w") as archive:
            archive.writestr(
                "nested/outlook.ics",
                fixture_path.read_text(encoding="utf-8"),
            )

        result = CalendarIngestionService().ingest(runtime=runtime)

        with runtime.session_factory() as session:
            sources = list(session.execute(select(Source)).scalars())
            events = list(session.execute(select(Event)).scalars())
            assets = list(session.execute(select(Asset)).scalars())

        assert result.status == "completed"
        assert result.processed_document_count == 1
        assert result.persisted_source_count == 1
        assert result.persisted_event_count == 1
        assert result.error_count == 0
        assert len(sources) == 1
        assert sources[0].type == "calendar"
        assert sources[0].external_id == "{0000002E-4C28-07C7-8A98-F77FE2214668}"
        assert len(events) == 1
        assert events[0].type == "calendar"
        assert events[0].title == "My Appointment"
        assert events[0].summary == "...some long html file content..."
        assert assets == []
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_calendar_ingestion_recurses_through_directory_ics_and_zip_inputs() -> None:
    workspace_root = _create_workspace_root()
    nested_root = workspace_root / "nested"
    nested_root.mkdir()
    direct_path = nested_root / "work.ics"
    archive_path = workspace_root / "archives.zip"
    runtime = _create_runtime(calendar_root=workspace_root)
    try:
        direct_path.write_text(
            _build_calendar_document(
                external_id="direct-cal",
                name="Direct",
                events=(("event-1", "20240102T090000Z", None, "Direct Event", None),),
            ),
            encoding="utf-8",
        )
        with zipfile.ZipFile(archive_path, mode="w") as archive:
            archive.writestr(
                "deep/archive.ics",
                _build_calendar_document(
                    external_id="zip-cal",
                    name="Archive",
                    events=(("event-2", "20240103T100000Z", None, "Archived Event", None),),
                ),
            )

        result = CalendarIngestionService().ingest(runtime=runtime)

        with runtime.session_factory() as session:
            sources = list(
                session.execute(select(Source).order_by(Source.external_id)).scalars()
            )
            events = list(session.execute(select(Event).order_by(Event.title)).scalars())

        assert result.status == "completed"
        assert result.processed_document_count == 2
        assert result.persisted_source_count == 2
        assert result.persisted_event_count == 2
        assert [source.external_id for source in sources] == ["direct-cal", "zip-cal"]
        assert [event.title for event in events] == ["Archived Event", "Direct Event"]
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_calendar_ingestion_fixture_reports_unchanged_updated_and_missing_from_source(
) -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    before_fixture_path = (
        Path("test") / "assets" / "outlook_cal_fixture_update_remove_before.ics"
    )
    after_fixture_path = (
        Path("test") / "assets" / "outlook_cal_fixture_update_remove_after.ics"
    )
    calendar_path = workspace_root / "fixture.ics"
    try:
        calendar_path.write_text(
            before_fixture_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        first_result = CalendarIngestionService().ingest(
            runtime=runtime,
            root=calendar_path,
        )

        calendar_path.write_text(
            after_fixture_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        second_result = CalendarIngestionService().ingest(
            runtime=runtime,
            root=calendar_path,
        )

        with runtime.session_factory() as session:
            job_runs = list(
                session.execute(select(JobRun).order_by(JobRun.id)).scalars()
            )

        assert first_result.status == "completed"
        assert second_result.status == "completed"
        assert len(job_runs) == 2
        assert job_runs[1].progress_json == {
            "total": 1,
            "completed": 1,
            "inserted": 1,
            "updated": 0,
            "unchanged": 1,
            "skipped": 0,
            "failed": 0,
            "missing_from_source": 2,
            "persisted_event_count": 2,
        }
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_calendar_ingestion_real_world_fixture_reports_only_missing_from_source(
) -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    before_fixture_path = Path("test") / "assets" / "outlook_cal_fixture_double_uid_start_end_before.ics"
    after_fixture_path = Path("test") / "assets" / "outlook_cal_fixture_double_uid_start_end_after.ics"
    calendar_path = workspace_root / "real-world.ics"
    try:
        calendar_path.write_text(
            before_fixture_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        first_result = CalendarIngestionService().ingest(
            runtime=runtime,
            root=calendar_path,
        )

        calendar_path.write_text(
            after_fixture_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        second_result = CalendarIngestionService().ingest(
            runtime=runtime,
            root=calendar_path,
        )

        with runtime.session_factory() as session:
            job_runs = list(
                session.execute(select(JobRun).order_by(JobRun.id)).scalars()
            )
            event_count = session.execute(select(Event)).scalars().all()

        assert first_result.status == "completed"
        assert second_result.status == "completed"
        assert len(job_runs) == 2
        assert len(event_count) == 4
        assert job_runs[1].progress_json == {
            "total": 1,
            "completed": 1,
            "inserted": 0,
            "updated": 0,
            "unchanged": 4,
            "skipped": 0,
            "failed": 0,
            "missing_from_source": 1,
            "persisted_event_count": 4,
        }
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def _create_runtime(*, calendar_root: Path | None = None):
    runtime = create_runtime_context(
        settings=Settings(database_url="sqlite://", calendar_root=calendar_root)
    )
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
