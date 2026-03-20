"""CLI smoke tests."""

import importlib
import io
import logging
import os
import shutil
import subprocess
import sys
import tomllib
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from pixelpast.analytics.entrypoints import list_supported_derive_jobs
from pixelpast.cli.main import (
    UI_WORKSPACE,
    CliProgressReporter,
    IngestionCliProgressReporter,
    _build_dev_process_specs,
    app,
)
from pixelpast.ingestion.entrypoints import list_supported_ingest_sources
from pixelpast.ingestion.workdays_vacation.contracts import (
    WorkdaysVacationIngestionResult,
    WorkdaysVacationTransformError,
    WorkdaysVacationWorkbookDescriptor,
)
from pixelpast.persistence.models import (
    Asset,
    DailyAggregate,
    DailyView,
    Event,
    JobRun,
    Source,
)
from pixelpast.shared.logging import KeyValueFormatter
from pixelpast.shared.progress import JobProgressSnapshot
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import get_settings

runner = CliRunner()
cli_main_module = importlib.import_module("pixelpast.cli.main")


def test_cli_help_lists_available_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "dev" in result.stdout
    assert "ingest" in result.stdout
    assert "derive" in result.stdout


def test_cli_ingest_help_lists_supported_sources() -> None:
    result = runner.invoke(app, ["ingest", "--help"])

    assert result.exit_code == 0
    for source in list_supported_ingest_sources():
        assert source in result.stdout


def test_cli_derive_help_lists_supported_jobs() -> None:
    result = runner.invoke(app, ["derive", "--help"])

    assert result.exit_code == 0
    for job in list_supported_derive_jobs():
        assert job in result.stdout


def test_build_dev_process_specs_returns_api_and_ui_commands(monkeypatch) -> None:
    monkeypatch.setattr(cli_main_module, "_resolve_npm_executable", lambda: "npm")

    api_process, ui_process = _build_dev_process_specs(
        demo=True,
        api_host="127.0.0.1",
        api_port=8000,
        ui_host="127.0.0.1",
        ui_port=5173,
    )

    assert api_process.name == "api"
    assert api_process.cwd == Path.cwd()
    assert api_process.command[:3] == (sys.executable, "-m", "uvicorn")
    assert api_process.command[-4:] == ("--host", "127.0.0.1", "--port", "8000")
    assert api_process.env is not None
    assert api_process.env["PIXELPAST_TIMELINE_PROJECTION_PROVIDER"] == "demo"

    assert ui_process.name == "ui"
    assert ui_process.cwd == UI_WORKSPACE
    assert ui_process.env is not None
    assert ui_process.command == (
        "npm",
        "run",
        "dev",
        "--",
        "--host",
        "127.0.0.1",
        "--port",
        "5173",
    )


def test_cli_ingest_photos_persists_assets(monkeypatch) -> None:
    database_path = _build_test_database_path("cli-ingest")
    photos_root = Path("var") / f"cli-photos-{uuid4().hex}"
    photos_root.mkdir(parents=True, exist_ok=False)
    (photos_root / "IMG_20240102_030405.jpg").write_bytes(b"not-a-real-image")
    monkeypatch.setenv(
        "PIXELPAST_DATABASE_URL", f"sqlite:///{database_path.as_posix()}"
    )
    monkeypatch.setenv("PIXELPAST_PHOTOS_ROOT", str(photos_root))
    get_settings.cache_clear()

    try:
        result = runner.invoke(app, ["ingest", "photos"])
        assert result.exit_code == 0
        assert database_path.exists()
        assert "[photos] completed" in result.stdout
        assert "inserted: 1" in result.stdout
        assert "failed: 0" in result.stdout

        engine = create_engine(f"sqlite:///{database_path.as_posix()}")
        try:
            with Session(engine) as session:
                assets = list(session.execute(select(Asset)).scalars())
                job_runs = list(session.execute(select(JobRun)).scalars())

            assert len(assets) == 1
            assert len(job_runs) == 1
            assert job_runs[0].type == "ingest"
            assert job_runs[0].job == "photos"
            assert job_runs[0].status == "completed"
            assert job_runs[0].phase == "finalization"
            assert job_runs[0].last_heartbeat_at is not None
            assert job_runs[0].progress_json is not None
            assert job_runs[0].progress_json["inserted"] == 1
            assert job_runs[0].progress_json["failed"] == 0
        finally:
            engine.dispose()
    finally:
        get_settings.cache_clear()
        if database_path.exists():
            database_path.unlink()
        shutil.rmtree(photos_root, ignore_errors=True)


def test_cli_ingest_photos_subprocess_completes_with_fixture_assets() -> None:
    database_path = _build_test_database_path("cli-ingest-fixtures")
    photos_root = Path("test") / "assets"
    environment = os.environ.copy()
    environment["PIXELPAST_DATABASE_URL"] = (
        f"sqlite:///{database_path.resolve().as_posix()}"
    )
    environment["PIXELPAST_PHOTOS_ROOT"] = str(photos_root.resolve())

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pixelpast.cli.main", "ingest", "photos"],
            cwd=Path.cwd(),
            env=environment,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )

        assert result.returncode == 0, result.stderr
        assert database_path.exists()
        assert "[photos] completed" in result.stdout
        assert "inserted: 3" in result.stdout
        assert "missing_from_source: 0" in result.stdout

        engine = create_engine(f"sqlite:///{database_path.as_posix()}")
        try:
            with Session(engine) as session:
                assets = list(
                    session.execute(select(Asset).order_by(Asset.external_id)).scalars()
                )
                job_runs = list(
                    session.execute(select(JobRun).order_by(JobRun.id)).scalars()
                )
        finally:
            engine.dispose()

        assert len(assets) == 3
        assert [Path(asset.external_id).name for asset in assets] == [
            "monalisa-1.jpg",
            "monalisa-2.jpg",
            "monalisa-3.jpg",
        ]
        assert assets[2].summary == "Title 3 äöüßÄÖÜ"
        assert len(job_runs) == 1
        assert job_runs[0].type == "ingest"
        assert job_runs[0].job == "photos"
        assert job_runs[0].status == "completed"
        assert job_runs[0].phase == "finalization"
        assert job_runs[0].last_heartbeat_at is not None
        assert job_runs[0].progress_json is not None
        assert job_runs[0].progress_json["inserted"] == 3
        assert job_runs[0].progress_json["failed"] == 0
        assert job_runs[0].progress_json["missing_from_source"] == 0
    finally:
        if database_path.exists():
            database_path.unlink()


def test_cli_ingest_calendar_persists_events_from_fixture(monkeypatch) -> None:
    database_path = _build_test_database_path("cli-calendar-ingest")
    fixture_path = Path("test") / "assets" / "outlook_cal_export_test_fixture.ics"
    monkeypatch.setenv(
        "PIXELPAST_DATABASE_URL", f"sqlite:///{database_path.as_posix()}"
    )
    monkeypatch.setenv("PIXELPAST_CALENDAR_ROOT", str(fixture_path.resolve()))
    get_settings.cache_clear()

    try:
        result = runner.invoke(app, ["ingest", "calendar"])
        assert result.exit_code == 0
        assert database_path.exists()
        assert "[calendar] completed" in result.stdout
        assert "inserted: 1" in result.stdout
        assert "failed: 0" in result.stdout

        engine = create_engine(f"sqlite:///{database_path.as_posix()}")
        try:
            with Session(engine) as session:
                sources = list(session.execute(select(Source)).scalars())
                events = list(session.execute(select(Event)).scalars())
                assets = list(session.execute(select(Asset)).scalars())
                job_runs = list(
                    session.execute(select(JobRun).order_by(JobRun.id)).scalars()
                )
        finally:
            engine.dispose()

        assert len(sources) == 1
        assert sources[0].type == "calendar"
        assert sources[0].external_id == "{0000002E-4C28-07C7-8A98-F77FE2214668}"
        assert len(events) == 1
        assert events[0].type == "calendar"
        assert events[0].title == "My Appointment"
        assert events[0].summary == "...some long html file content..."
        assert assets == []
        assert len(job_runs) == 1
        assert job_runs[0].type == "ingest"
        assert job_runs[0].job == "calendar"
        assert job_runs[0].status == "completed"
        assert job_runs[0].progress_json is not None
        assert job_runs[0].progress_json["inserted"] == 1
        assert job_runs[0].progress_json["failed"] == 0
    finally:
        get_settings.cache_clear()
        if database_path.exists():
            database_path.unlink()


def test_cli_ingest_calendar_subprocess_completes_with_zip_fixture() -> None:
    database_path = _build_test_database_path("cli-calendar-ingest-zip")
    workspace_root = Path("var") / f"cli-calendar-{uuid4().hex}"
    fixture_path = Path("test") / "assets" / "outlook_cal_export_test_fixture.ics"
    archive_path = workspace_root / "calendar.zip"
    workspace_root.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(archive_path, mode="w") as archive:
        archive.writestr("nested/outlook.ics", fixture_path.read_text(encoding="utf-8"))

    environment = os.environ.copy()
    environment["PIXELPAST_DATABASE_URL"] = (
        f"sqlite:///{database_path.resolve().as_posix()}"
    )
    environment["PIXELPAST_CALENDAR_ROOT"] = str(archive_path.resolve())

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pixelpast.cli.main", "ingest", "calendar"],
            cwd=Path.cwd(),
            env=environment,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )

        assert result.returncode == 0, result.stderr
        assert "[calendar] completed" in result.stdout
        assert "inserted: 1" in result.stdout
    finally:
        if database_path.exists():
            database_path.unlink()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_cli_ingest_spotify_persists_events_from_fixture(monkeypatch) -> None:
    database_path = _build_test_database_path("cli-spotify-ingest")
    workspace_root = Path("var") / f"cli-spotify-{uuid4().hex}"
    fixture_path = (
        Path("test") / "assets" / "spotify_streaming_history_audio_test_fixture.json"
    )
    spotify_path = workspace_root / "Streaming_History_Audio_2024.json"
    workspace_root.mkdir(parents=True, exist_ok=False)
    spotify_path.write_text(fixture_path.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setenv(
        "PIXELPAST_DATABASE_URL", f"sqlite:///{database_path.as_posix()}"
    )
    monkeypatch.setenv("PIXELPAST_SPOTIFY_ROOT", str(spotify_path.resolve()))
    get_settings.cache_clear()

    try:
        result = runner.invoke(app, ["ingest", "spotify"])
        assert result.exit_code == 0
        assert database_path.exists()
        assert "[spotify] completed" in result.stdout
        assert "inserted: 2" in result.stdout
        assert "skipped_json_files: 0" in result.stdout
        assert "failed: 0" in result.stdout

        engine = create_engine(f"sqlite:///{database_path.as_posix()}")
        try:
            with Session(engine) as session:
                sources = list(session.execute(select(Source)).scalars())
                events = list(
                    session.execute(
                        select(Event).order_by(Event.timestamp_end)
                    ).scalars()
                )
                assets = list(session.execute(select(Asset)).scalars())
                job_runs = list(
                    session.execute(select(JobRun).order_by(JobRun.id)).scalars()
                )
        finally:
            engine.dispose()

        assert len(sources) == 1
        assert sources[0].type == "spotify"
        assert sources[0].external_id == "spotify:pixeluser"
        assert len(events) == 2
        assert [event.type for event in events] == ["music_play", "music_play"]
        assert assets == []
        assert len(job_runs) == 1
        assert job_runs[0].type == "ingest"
        assert job_runs[0].job == "spotify"
        assert job_runs[0].status == "completed"
        assert job_runs[0].progress_json is not None
        assert job_runs[0].progress_json["inserted"] == 2
        assert job_runs[0].progress_json["persisted_event_count"] == 2
        assert job_runs[0].progress_json["failed"] == 0
    finally:
        get_settings.cache_clear()
        if database_path.exists():
            database_path.unlink()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_cli_ingest_spotify_zip_reports_skipped_json_files(monkeypatch) -> None:
    database_path = _build_test_database_path("cli-spotify-zip-ingest")
    workspace_root = Path("var") / f"cli-spotify-zip-{uuid4().hex}"
    archive_path = workspace_root / "spotify-export.zip"
    workspace_root.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(archive_path, mode="w") as archive:
        archive.writestr(
            "nested/Streaming_History_Audio_2024.json",
            "\n".join(
                [
                    "[",
                    "  {",
                    '    "ts": "2024-02-01T07:15:10Z",',
                    '    "username": "PixelUser",',
                    '    "platform": "android",',
                    '    "ms_played": 1000,',
                    '    "conn_country": "DE",',
                    '    "master_metadata_track_name": "One",',
                    '    "master_metadata_album_artist_name": "Artist",',
                    '    "spotify_track_uri": "spotify:track:one",',
                    '    "episode_name": null,',
                    '    "episode_show_name": null,',
                    '    "spotify_episode_uri": null,',
                    '    "shuffle": false,',
                    '    "skipped": false',
                    "  }",
                    "]",
                ]
            ),
        )
        archive.writestr("nested/Profile.json", "{}")
    monkeypatch.setenv(
        "PIXELPAST_DATABASE_URL", f"sqlite:///{database_path.as_posix()}"
    )
    monkeypatch.setenv("PIXELPAST_SPOTIFY_ROOT", str(archive_path.resolve()))
    get_settings.cache_clear()

    try:
        result = runner.invoke(app, ["ingest", "spotify"])

        assert result.exit_code == 0
        assert "[spotify] completed" in result.stdout
        assert "skipped_json_files: 1" in result.stdout
        assert "inserted: 1" in result.stdout
    finally:
        get_settings.cache_clear()
        if database_path.exists():
            database_path.unlink()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_cli_ingest_spotify_warns_when_export_has_no_usernames(monkeypatch) -> None:
    database_path = _build_test_database_path("cli-spotify-missing-username")
    workspace_root = Path("var") / f"cli-spotify-missing-user-{uuid4().hex}"
    spotify_path = workspace_root / "Streaming_History_Audio_2024.json"
    workspace_root.mkdir(parents=True, exist_ok=False)
    spotify_path.write_text(
        "\n".join(
            [
                "[",
                "  {",
                '    "ts": "2024-02-01T07:15:10Z",',
                '    "username": "",',
                '    "platform": "android",',
                '    "ms_played": 1000,',
                '    "conn_country": "DE",',
                '    "master_metadata_track_name": "One",',
                '    "master_metadata_album_artist_name": "Artist",',
                '    "spotify_track_uri": "spotify:track:one",',
                '    "episode_name": null,',
                '    "episode_show_name": null,',
                '    "spotify_episode_uri": null,',
                '    "shuffle": false,',
                '    "skipped": false',
                "  }",
                "]",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("PIXELPAST_DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    monkeypatch.setenv("PIXELPAST_SPOTIFY_ROOT", str(spotify_path.resolve()))
    get_settings.cache_clear()

    try:
        result = runner.invoke(app, ["ingest", "spotify"])

        assert result.exit_code == 0
        assert "[spotify] completed" in result.stdout
        assert "warning: Spotify export rows are missing 'username'" in result.stderr
        assert "inserted: 1" in result.stdout
    finally:
        get_settings.cache_clear()
        if database_path.exists():
            database_path.unlink()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_cli_ingest_calendar_reports_event_counts_in_terminal_summary(
    monkeypatch,
) -> None:
    database_path = _build_test_database_path("cli-calendar-ingest-summary")
    workspace_root = Path("var") / f"cli-calendar-summary-{uuid4().hex}"
    calendar_path = workspace_root / "work.ics"
    workspace_root.mkdir(parents=True, exist_ok=False)
    monkeypatch.setenv(
        "PIXELPAST_DATABASE_URL", f"sqlite:///{database_path.as_posix()}"
    )
    monkeypatch.setenv("PIXELPAST_CALENDAR_ROOT", str(calendar_path.resolve()))
    get_settings.cache_clear()

    calendar_path.write_text(
        "\n".join(
            [
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                "X-WR-CALNAME:Work",
                "X-WR-RELCALID:cli-calendar-summary",
                "BEGIN:VEVENT",
                "UID:event-1",
                "DTSTART:20240102T090000Z",
                "SUMMARY:Event One",
                "END:VEVENT",
                "BEGIN:VEVENT",
                "UID:event-2",
                "DTSTART:20240103T090000Z",
                "SUMMARY:Event Two",
                "END:VEVENT",
                "END:VCALENDAR",
                "",
            ]
        ),
        encoding="utf-8",
    )

    try:
        result = runner.invoke(app, ["ingest", "calendar"])

        assert result.exit_code == 0
        assert "[calendar] completed" in result.stdout
        assert "inserted: 2" in result.stdout

        engine = create_engine(f"sqlite:///{database_path.as_posix()}")
        try:
            with Session(engine) as session:
                job_run = session.execute(
                    select(JobRun).order_by(JobRun.id.desc())
                ).scalar_one()
        finally:
            engine.dispose()

        assert job_run.progress_json is not None
        assert job_run.progress_json["inserted"] == 2
        assert job_run.progress_json["persisted_event_count"] == 2
    finally:
        get_settings.cache_clear()
        if database_path.exists():
            database_path.unlink()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_cli_ingest_calendar_reports_missing_from_source_for_removed_events(
    monkeypatch,
) -> None:
    database_path = _build_test_database_path("cli-calendar-missing-from-source")
    workspace_root = Path("var") / f"cli-calendar-missing-{uuid4().hex}"
    calendar_path = workspace_root / "work.ics"
    workspace_root.mkdir(parents=True, exist_ok=False)
    monkeypatch.setenv(
        "PIXELPAST_DATABASE_URL", f"sqlite:///{database_path.as_posix()}"
    )
    monkeypatch.setenv("PIXELPAST_CALENDAR_ROOT", str(calendar_path.resolve()))
    get_settings.cache_clear()

    try:
        calendar_path.write_text(
            "\n".join(
                [
                    "BEGIN:VCALENDAR",
                    "VERSION:2.0",
                    "X-WR-CALNAME:Work",
                    "X-WR-RELCALID:cli-calendar-delete-sync",
                    "BEGIN:VEVENT",
                    "UID:event-1",
                    "DTSTART:20240102T090000Z",
                    "SUMMARY:Event One",
                    "END:VEVENT",
                    "BEGIN:VEVENT",
                    "UID:event-2",
                    "DTSTART:20240103T090000Z",
                    "SUMMARY:Event Two",
                    "END:VEVENT",
                    "END:VCALENDAR",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        first_result = runner.invoke(app, ["ingest", "calendar"])
        assert first_result.exit_code == 0

        calendar_path.write_text(
            "\n".join(
                [
                    "BEGIN:VCALENDAR",
                    "VERSION:2.0",
                    "X-WR-CALNAME:Work",
                    "X-WR-RELCALID:cli-calendar-delete-sync",
                    "BEGIN:VEVENT",
                    "UID:event-1",
                    "DTSTART:20240102T090000Z",
                    "SUMMARY:Event One",
                    "END:VEVENT",
                    "END:VCALENDAR",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = runner.invoke(app, ["ingest", "calendar"])

        assert result.exit_code == 0
        assert "[calendar] completed" in result.stdout
        assert "unchanged: 1" in result.stdout
        assert "missing_from_source: 1" in result.stdout

        engine = create_engine(f"sqlite:///{database_path.as_posix()}")
        try:
            with Session(engine) as session:
                events = list(
                    session.execute(
                        select(Event).order_by(Event.timestamp_start)
                    ).scalars()
                )
                job_run = (
                    session.execute(select(JobRun).order_by(JobRun.id.desc()))
                    .scalars()
                    .first()
                )
        finally:
            engine.dispose()

        assert [event.title for event in events] == ["Event One"]
        assert job_run is not None
        assert job_run.progress_json is not None
        assert job_run.progress_json["unchanged"] == 1
        assert job_run.progress_json["missing_from_source"] == 1
    finally:
        get_settings.cache_clear()
        if database_path.exists():
            database_path.unlink()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_cli_ingest_workdays_vacation_persists_source_from_fixture(
    monkeypatch,
) -> None:
    database_path = _build_test_database_path("cli-workdays-vacation-ingest")
    fixture_path = Path("test") / "assets" / "workday_vacation_test_fixture.xlsx"
    monkeypatch.setenv(
        "PIXELPAST_DATABASE_URL", f"sqlite:///{database_path.as_posix()}"
    )
    monkeypatch.setenv(
        "PIXELPAST_WORKDAYS_VACATION_ROOT",
        str(fixture_path.resolve()),
    )
    get_settings.cache_clear()

    try:
        result = runner.invoke(app, ["ingest", "workdays_vacation"])
        assert result.exit_code == 0
        assert database_path.exists()
        assert "[workdays_vacation] completed" in result.stdout
        assert "inserted: 522" in result.stdout
        assert "skipped: 207" in result.stdout
        assert "failed: 0" in result.stdout

        engine = create_engine(f"sqlite:///{database_path.as_posix()}")
        try:
            with Session(engine) as session:
                sources = list(session.execute(select(Source)).scalars())
                events = list(session.execute(select(Event)).scalars())
                job_runs = list(
                    session.execute(select(JobRun).order_by(JobRun.id)).scalars()
                )
        finally:
            engine.dispose()

        assert len(sources) == 1
        assert sources[0].type == "workdays_vacation"
        assert sources[0].external_id == fixture_path.resolve().as_posix()
        assert sources[0].config["origin_path"] == fixture_path.resolve().as_posix()
        assert sources[0].config["sheet_names"]
        assert len(events) == 522
        assert len(job_runs) == 1
        assert job_runs[0].type == "ingest"
        assert job_runs[0].job == "workdays_vacation"
        assert job_runs[0].status == "completed"
        assert job_runs[0].progress_json is not None
        assert job_runs[0].progress_json["inserted"] == 522
        assert job_runs[0].progress_json["skipped"] == 207
        assert job_runs[0].progress_json["failed"] == 0
    finally:
        get_settings.cache_clear()
        if database_path.exists():
            database_path.unlink()


def test_cli_returns_invalid_argument_exit_code_when_workdays_vacation_root_is_missing(
    monkeypatch,
) -> None:
    database_path = _build_test_database_path("cli-workdays-vacation-missing-root")
    monkeypatch.setenv(
        "PIXELPAST_DATABASE_URL", f"sqlite:///{database_path.as_posix()}"
    )
    monkeypatch.delenv("PIXELPAST_WORKDAYS_VACATION_ROOT", raising=False)
    get_settings.cache_clear()

    try:
        result = runner.invoke(app, ["ingest", "workdays_vacation"])
        assert result.exit_code == 2
        assert "error: Workdays vacation ingestion requires" in result.stderr
    finally:
        get_settings.cache_clear()
        if database_path.exists():
            database_path.unlink()


def test_cli_ingest_workdays_vacation_prints_transform_errors(
    monkeypatch,
) -> None:
    database_path = _build_test_database_path("cli-workdays-vacation-errors")
    monkeypatch.setenv(
        "PIXELPAST_DATABASE_URL", f"sqlite:///{database_path.as_posix()}"
    )
    get_settings.cache_clear()

    workbook_path = Path("test") / "assets" / "broken_workday_vacation.xlsx"
    fake_result = WorkdaysVacationIngestionResult(
        run_id=7,
        processed_workbook_count=0,
        persisted_source_count=0,
        persisted_event_count=0,
        error_count=1,
        status="partial_failure",
        transform_errors=(
            WorkdaysVacationTransformError(
                workbook=WorkdaysVacationWorkbookDescriptor(path=workbook_path),
                message="Legend color '#123456' is missing from the workbook.",
            ),
        ),
    )
    monkeypatch.setattr(cli_main_module, "run_ingest_source", lambda **_: fake_result)

    try:
        result = runner.invoke(app, ["ingest", "workdays_vacation"])
        assert result.exit_code == 0
        assert (
            "error: "
            f"{workbook_path.resolve().as_posix()}: "
            "Legend color '#123456' is missing from the workbook."
        ) in result.stderr
    finally:
        get_settings.cache_clear()
        if database_path.exists():
            database_path.unlink()


def test_ingestion_cli_progress_reporter_tracks_phase_progress() -> None:
    stream = io.StringIO()
    reporter = IngestionCliProgressReporter(stream=stream)

    reporter(
        JobProgressSnapshot(
            event="phase_started",
            job_type="ingest",
            job="photos",
            run_id=1,
            phase="metadata extraction",
            status="running",
            total=3,
            completed=0,
            inserted=0,
            updated=0,
            unchanged=0,
            skipped=0,
            failed=0,
            missing_from_source=0,
            heartbeat_written=False,
        )
    )
    reporter(
        JobProgressSnapshot(
            event="progress",
            job_type="ingest",
            job="photos",
            run_id=1,
            phase="metadata extraction",
            status="running",
            total=3,
            completed=3,
            inserted=0,
            updated=0,
            unchanged=0,
            skipped=0,
            failed=0,
            missing_from_source=0,
            heartbeat_written=False,
        )
    )

    assert reporter.active_phase == "metadata extraction"
    assert reporter.active_completed == 3
    assert reporter.active_total == 3


def test_cli_progress_reporter_prints_derive_terminal_summary() -> None:
    stream = io.StringIO()
    reporter = CliProgressReporter(stream=stream)

    reporter(
        JobProgressSnapshot(
            event="run_finished",
            job_type="derive",
            job="daily-aggregate",
            run_id=7,
            phase="finalization",
            status="completed",
            total=1,
            completed=1,
            inserted=5,
            updated=0,
            unchanged=0,
            skipped=0,
            failed=0,
            missing_from_source=0,
            heartbeat_written=True,
        )
    )

    _assert_lines_present(
        stream.getvalue(),
        [
            "[daily-aggregate] completed",
            "run_id: 7",
            "status: completed",
            "inserted: 5",
            "updated: 0",
            "unchanged: 0",
            "skipped: 0",
            "failed: 0",
            "missing_from_source: 0",
        ],
    )


def test_cli_progress_reporter_prints_failure_summary() -> None:
    stream = io.StringIO()
    reporter = CliProgressReporter(stream=stream)

    reporter(
        JobProgressSnapshot(
            event="run_failed",
            job_type="derive",
            job="daily-aggregate",
            run_id=11,
            phase="persisting daily aggregates",
            status="failed",
            total=5,
            completed=3,
            inserted=2,
            updated=0,
            unchanged=0,
            skipped=0,
            failed=1,
            missing_from_source=0,
            heartbeat_written=True,
        )
    )

    _assert_lines_present(
        stream.getvalue(),
        [
            "[daily-aggregate] failed",
            "run_id: 11",
            "status: failed",
            "phase: persisting daily aggregates",
            "progress: 3/5",
            "inserted: 2",
            "updated: 0",
            "unchanged: 0",
            "skipped: 0",
            "failed: 1",
            "missing_from_source: 0",
        ],
    )


def test_cli_derive_daily_aggregate_rebuilds_rows(monkeypatch) -> None:
    database_path = _build_test_database_path("cli-derive")
    monkeypatch.setenv(
        "PIXELPAST_DATABASE_URL", f"sqlite:///{database_path.as_posix()}"
    )
    get_settings.cache_clear()

    try:
        runtime = create_runtime_context(
            settings=get_settings(),
        )
        try:
            initialize_database(runtime)
            with runtime.session_factory() as session:
                source = Source(name="Calendar", type="calendar", config={})
                session.add(source)
                session.flush()
                session.add_all(
                    [
                        Event(
                            source_id=source.id,
                            type="calendar",
                            timestamp_start=datetime(2024, 1, 2, 8, 0, tzinfo=UTC),
                            timestamp_end=None,
                            title="Morning plan",
                            summary=None,
                            latitude=None,
                            longitude=None,
                            raw_payload={},
                            derived_payload={},
                        ),
                        Event(
                            source_id=source.id,
                            type="calendar",
                            timestamp_start=datetime(2024, 1, 2, 17, 0, tzinfo=UTC),
                            timestamp_end=None,
                            title="Evening plan",
                            summary=None,
                            latitude=None,
                            longitude=None,
                            raw_payload={},
                            derived_payload={},
                        ),
                        Asset(
                            external_id="photo-1",
                            media_type="photo",
                            timestamp=datetime(2024, 1, 2, 9, 30, tzinfo=UTC),
                            latitude=None,
                            longitude=None,
                            metadata_json={},
                        ),
                        Asset(
                            external_id="photo-2",
                            media_type="photo",
                            timestamp=datetime(2024, 1, 3, 12, 0, tzinfo=UTC),
                            latitude=None,
                            longitude=None,
                            metadata_json={},
                        ),
                    ]
                )
                session.commit()
        finally:
            runtime.engine.dispose()

        result = runner.invoke(app, ["derive", "daily-aggregate"])
        assert result.exit_code == 0
        assert database_path.exists()
        assert "[daily-aggregate] completed" in result.stdout
        assert "run_id: 1" in result.stdout
        assert "inserted: 5" in result.stdout
        assert "failed: 0" in result.stdout

        engine = create_engine(f"sqlite:///{database_path.as_posix()}")
        try:
            with Session(engine) as session:
                aggregates = list(
                    session.execute(
                        select(DailyAggregate)
                        .join(DailyView, DailyView.id == DailyAggregate.daily_view_id)
                        .order_by(
                            DailyAggregate.date,
                            DailyView.aggregate_scope,
                            DailyView.source_type,
                        )
                    ).scalars()
                )
                job_runs = list(
                    session.execute(select(JobRun).order_by(JobRun.id)).scalars()
                )
        finally:
            engine.dispose()

        assert [
            (
                aggregate.date.isoformat(),
                aggregate.aggregate_scope,
                aggregate.source_type,
                aggregate.total_events,
                aggregate.media_count,
                aggregate.activity_score,
            )
            for aggregate in aggregates
        ] == [
            ("2024-01-02", "overall", "__all__", 2, 1, 3),
            ("2024-01-02", "source_type", "calendar", 2, 0, 2),
            ("2024-01-02", "source_type", "photo", 0, 1, 1),
            ("2024-01-03", "overall", "__all__", 0, 1, 1),
            ("2024-01-03", "source_type", "photo", 0, 1, 1),
        ]
        assert len(job_runs) == 1
        assert job_runs[0].type == "derive"
        assert job_runs[0].job == "daily-aggregate"
        assert job_runs[0].mode == "full"
        assert job_runs[0].status == "completed"
        assert job_runs[0].phase == "finalization"
        assert job_runs[0].progress_json is not None
        assert job_runs[0].progress_json["inserted"] == 5
    finally:
        get_settings.cache_clear()
        if database_path.exists():
            database_path.unlink()


def test_cli_derive_daily_aggregate_range_reports_progress(monkeypatch) -> None:
    database_path = _build_test_database_path("cli-derive-range")
    monkeypatch.setenv(
        "PIXELPAST_DATABASE_URL", f"sqlite:///{database_path.as_posix()}"
    )
    get_settings.cache_clear()

    try:
        runtime = create_runtime_context(settings=get_settings())
        try:
            initialize_database(runtime)
            with runtime.session_factory() as session:
                source = Source(name="Calendar", type="calendar", config={})
                session.add(source)
                session.flush()
                session.add_all(
                    [
                        Event(
                            source_id=source.id,
                            type="calendar",
                            timestamp_start=datetime(2024, 1, 1, 8, 0, tzinfo=UTC),
                            timestamp_end=None,
                            title="Day one",
                            summary=None,
                            latitude=None,
                            longitude=None,
                            raw_payload={},
                            derived_payload={},
                        ),
                        Event(
                            source_id=source.id,
                            type="calendar",
                            timestamp_start=datetime(2024, 1, 2, 9, 0, tzinfo=UTC),
                            timestamp_end=None,
                            title="Day two",
                            summary=None,
                            latitude=None,
                            longitude=None,
                            raw_payload={},
                            derived_payload={},
                        ),
                        Asset(
                            external_id="asset-1",
                            media_type="photo",
                            timestamp=datetime(2024, 1, 2, 10, 0, tzinfo=UTC),
                            latitude=None,
                            longitude=None,
                            metadata_json={},
                        ),
                        Asset(
                            external_id="asset-2",
                            media_type="photo",
                            timestamp=datetime(2024, 1, 3, 11, 0, tzinfo=UTC),
                            latitude=None,
                            longitude=None,
                            metadata_json={},
                        ),
                    ]
                )
                session.commit()
        finally:
            runtime.engine.dispose()

        result = runner.invoke(
            app,
            [
                "derive",
                "daily-aggregate",
                "--start-date",
                "2024-01-02",
                "--end-date",
                "2024-01-02",
            ],
        )

        assert result.exit_code == 0
        assert "[daily-aggregate] completed" in result.stdout
        assert "run_id: 1" in result.stdout
        assert "inserted: 3" in result.stdout
        assert "missing_from_source: 0" in result.stdout

        engine = create_engine(f"sqlite:///{database_path.as_posix()}")
        try:
            with Session(engine) as session:
                job_runs = list(
                    session.execute(select(JobRun).order_by(JobRun.id)).scalars()
                )
        finally:
            engine.dispose()

        assert len(job_runs) == 1
        assert job_runs[0].mode == "range"
        assert job_runs[0].progress_json is not None
        assert job_runs[0].progress_json["inserted"] == 3
    finally:
        get_settings.cache_clear()
        if database_path.exists():
            database_path.unlink()


def test_cli_returns_invalid_argument_exit_code_for_unknown_source(
    monkeypatch,
) -> None:
    database_path = _build_test_database_path("cli-invalid")
    monkeypatch.setenv(
        "PIXELPAST_DATABASE_URL", f"sqlite:///{database_path.as_posix()}"
    )
    get_settings.cache_clear()

    try:
        result = runner.invoke(app, ["ingest", "unknown-source"])
        assert result.exit_code == 2
    finally:
        get_settings.cache_clear()
        if database_path.exists():
            database_path.unlink()


def test_cli_returns_invalid_argument_exit_code_when_calendar_root_is_missing(
    monkeypatch,
) -> None:
    database_path = _build_test_database_path("cli-calendar-missing-root")
    monkeypatch.setenv(
        "PIXELPAST_DATABASE_URL", f"sqlite:///{database_path.as_posix()}"
    )
    monkeypatch.delenv("PIXELPAST_CALENDAR_ROOT", raising=False)
    get_settings.cache_clear()

    try:
        result = runner.invoke(app, ["ingest", "calendar"])
        assert result.exit_code == 2
    finally:
        get_settings.cache_clear()
        if database_path.exists():
            database_path.unlink()


def test_cli_returns_invalid_argument_exit_code_when_spotify_root_is_missing(
    monkeypatch,
) -> None:
    database_path = _build_test_database_path("cli-spotify-missing-root")
    monkeypatch.setenv(
        "PIXELPAST_DATABASE_URL", f"sqlite:///{database_path.as_posix()}"
    )
    monkeypatch.delenv("PIXELPAST_SPOTIFY_ROOT", raising=False)
    get_settings.cache_clear()

    try:
        result = runner.invoke(app, ["ingest", "spotify"])
        assert result.exit_code == 2
        assert "error: Spotify ingestion requires" in result.stderr
    finally:
        get_settings.cache_clear()
        if database_path.exists():
            database_path.unlink()


def test_cli_returns_invalid_argument_exit_code_for_unknown_derive_job(
    monkeypatch,
) -> None:
    database_path = _build_test_database_path("cli-invalid-derive")
    monkeypatch.setenv(
        "PIXELPAST_DATABASE_URL", f"sqlite:///{database_path.as_posix()}"
    )
    get_settings.cache_clear()

    try:
        result = runner.invoke(app, ["derive", "unknown-job"])
        assert result.exit_code == 2
    finally:
        get_settings.cache_clear()
        if database_path.exists():
            database_path.unlink()


def test_pyproject_registers_pixelpast_console_script() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["pixelpast"] == "pixelpast.cli.main:main"


def test_key_value_formatter_renders_structured_output() -> None:
    formatter = KeyValueFormatter()
    record = formatter.format(
        logging.makeLogRecord(
            {
                "name": "pixelpast.cli.main",
                "levelno": 20,
                "levelname": "INFO",
                "msg": "command started",
                "args": (),
                "command": "ingest",
                "target": "photos",
            }
        )
    )

    assert "level=info" in record
    assert "logger=pixelpast.cli.main" in record
    assert 'message="command started"' in record
    assert 'command="ingest"' in record
    assert 'target="photos"' in record


def _build_test_database_path(prefix: str) -> Path:
    """Return a unique SQLite test database path within the workspace."""

    database_dir = Path("var")
    database_dir.mkdir(exist_ok=True)
    return database_dir / f"{prefix}-{uuid4().hex}.db"


def _non_empty_lines(value: str) -> list[str]:
    """Return non-empty lines from captured CLI output."""

    return [line for line in value.splitlines() if line.strip()]


def _assert_lines_present(value: str, expected_lines: list[str]) -> None:
    """Assert that each expected line appears in captured CLI output."""

    lines = _non_empty_lines(value)
    for expected_line in expected_lines:
        assert expected_line in lines
