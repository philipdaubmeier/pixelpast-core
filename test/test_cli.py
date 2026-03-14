"""CLI smoke tests."""

import importlib
import logging
import os
import shutil
import subprocess
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from pixelpast.analytics.entrypoints import list_supported_derive_jobs
from pixelpast.cli.main import UI_WORKSPACE, _build_dev_process_specs, app
from pixelpast.ingestion.entrypoints import list_supported_ingest_sources
from pixelpast.persistence.models import Asset, DailyAggregate, Event, ImportRun, Source
from pixelpast.shared.logging import KeyValueFormatter
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
    monkeypatch.setenv("PIXELPAST_DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    monkeypatch.setenv("PIXELPAST_PHOTOS_ROOT", str(photos_root))
    get_settings.cache_clear()

    try:
        result = runner.invoke(app, ["ingest", "photos"])
        assert result.exit_code == 0
        assert database_path.exists()
        assert "phase=filesystem discovery" in result.stdout
        assert "phase=metadata extraction" in result.stdout
        assert "phase=canonical persistence" in result.stdout
        assert "[photos] summary status=completed" in result.stdout

        engine = create_engine(f"sqlite:///{database_path.as_posix()}")
        try:
            with Session(engine) as session:
                assets = list(session.execute(select(Asset)).scalars())
                import_runs = list(session.execute(select(ImportRun)).scalars())

            assert len(assets) == 1
            assert len(import_runs) == 1
            assert import_runs[0].status == "completed"
            assert import_runs[0].phase == "finalization"
            assert import_runs[0].last_heartbeat_at is not None
            assert import_runs[0].progress_json is not None
            assert import_runs[0].progress_json["inserted"] == 1
            assert import_runs[0].progress_json["failed"] == 0
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
        assert "phase=filesystem discovery" in result.stdout
        assert "phase=metadata extraction" in result.stdout
        assert "phase=canonical persistence" in result.stdout
        assert "summary status=completed" in result.stdout

        engine = create_engine(f"sqlite:///{database_path.as_posix()}")
        try:
            with Session(engine) as session:
                assets = list(
                    session.execute(select(Asset).order_by(Asset.external_id)).scalars()
                )
                import_runs = list(
                    session.execute(select(ImportRun).order_by(ImportRun.id)).scalars()
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
        assert len(import_runs) == 1
        assert import_runs[0].status == "completed"
        assert import_runs[0].phase == "finalization"
        assert import_runs[0].last_heartbeat_at is not None
        assert import_runs[0].progress_json is not None
        assert import_runs[0].progress_json["inserted"] == 3
        assert import_runs[0].progress_json["failed"] == 0
        assert import_runs[0].progress_json["missing_from_source"] == 0
    finally:
        if database_path.exists():
            database_path.unlink()


def test_cli_derive_daily_aggregate_rebuilds_rows(monkeypatch) -> None:
    database_path = _build_test_database_path("cli-derive")
    monkeypatch.setenv("PIXELPAST_DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
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

        engine = create_engine(f"sqlite:///{database_path.as_posix()}")
        try:
            with Session(engine) as session:
                aggregates = list(
                    session.execute(
                        select(DailyAggregate).order_by(
                            DailyAggregate.date,
                            DailyAggregate.aggregate_scope,
                            DailyAggregate.source_type,
                        )
                    ).scalars()
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
    finally:
        get_settings.cache_clear()
        if database_path.exists():
            database_path.unlink()


def test_cli_returns_invalid_argument_exit_code_for_unknown_source(
    monkeypatch,
) -> None:
    database_path = _build_test_database_path("cli-invalid")
    monkeypatch.setenv("PIXELPAST_DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    get_settings.cache_clear()

    try:
        result = runner.invoke(app, ["ingest", "unknown-source"])
        assert result.exit_code == 2
    finally:
        get_settings.cache_clear()
        if database_path.exists():
            database_path.unlink()


def test_cli_returns_invalid_argument_exit_code_for_unknown_derive_job(
    monkeypatch,
) -> None:
    database_path = _build_test_database_path("cli-invalid-derive")
    monkeypatch.setenv("PIXELPAST_DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
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

    assert 'level=info' in record
    assert 'logger=pixelpast.cli.main' in record
    assert 'message="command started"' in record
    assert 'command="ingest"' in record
    assert 'target="photos"' in record


def _build_test_database_path(prefix: str) -> Path:
    """Return a unique SQLite test database path within the workspace."""

    database_dir = Path("var")
    database_dir.mkdir(exist_ok=True)
    return database_dir / f"{prefix}-{uuid4().hex}.db"
