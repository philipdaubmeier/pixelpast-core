"""CLI smoke tests."""

import logging
import shutil
import tomllib
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from pixelpast.cli.main import app
from pixelpast.persistence.models import Asset, ImportRun
from pixelpast.shared.logging import KeyValueFormatter
from pixelpast.shared.settings import get_settings

runner = CliRunner()


def test_cli_help_lists_available_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "ingest" in result.stdout
    assert "derive" in result.stdout


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

        engine = create_engine(f"sqlite:///{database_path.as_posix()}")
        try:
            with Session(engine) as session:
                assets = list(session.execute(select(Asset)).scalars())
                import_runs = list(session.execute(select(ImportRun)).scalars())

            assert len(assets) == 1
            assert len(import_runs) == 1
            assert import_runs[0].status == "completed"
        finally:
            engine.dispose()
    finally:
        get_settings.cache_clear()
        if database_path.exists():
            database_path.unlink()
        shutil.rmtree(photos_root, ignore_errors=True)


def test_cli_derive_daily_aggregate_runs_stub(
    monkeypatch,
) -> None:
    database_path = _build_test_database_path("cli-derive")
    monkeypatch.setenv("PIXELPAST_DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    get_settings.cache_clear()

    try:
        result = runner.invoke(app, ["derive", "daily-aggregate"])
        assert result.exit_code == 0
        assert database_path.exists()
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
