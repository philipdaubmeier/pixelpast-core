"""CLI tests for the asset thumbnail derive job."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from typer.testing import CliRunner

from pixelpast.cli.main import app
from pixelpast.persistence.models import Asset, Source
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import Settings, get_settings

runner = CliRunner()


def test_cli_derive_asset_thumbnails_supports_renditions_and_force(
    monkeypatch,
) -> None:
    workspace_root = _create_workspace_dir(prefix="cli-asset-thumbnails")
    runtime = None
    try:
        fixture_path = _copy_fixture_image(
            workspace_root=workspace_root,
            fixture_name="monalisa-1.jpg",
        )
        database_path = workspace_root / "pixelpast.db"
        thumbs_root = workspace_root / "thumbs"
        monkeypatch.setenv(
            "PIXELPAST_DATABASE_URL",
            f"sqlite:///{database_path.as_posix()}",
        )
        monkeypatch.setenv("PIXELPAST_MEDIA_THUMB_ROOT", thumbs_root.as_posix())
        get_settings.cache_clear()

        runtime = create_runtime_context(
            settings=Settings(
                database_url=f"sqlite:///{database_path.as_posix()}",
                media_thumb_root=thumbs_root,
            )
        )
        initialize_database(runtime)
        _insert_photo_asset(
            runtime=runtime,
            short_id="CLITHMB1",
            source_type="photos",
            external_id=fixture_path.as_posix(),
        )
        runtime.engine.dispose()
        runtime = None

        first_result = runner.invoke(
            app,
            [
                "derive",
                "asset-thumbnails",
                "--rendition",
                "h120",
                "--rendition",
                "q200",
            ],
        )
        assert first_result.exit_code == 0
        assert "[asset-thumbnails] completed" in first_result.stdout
        assert (thumbs_root / "h120" / "CLITHMB1.webp").exists()
        assert (thumbs_root / "q200" / "CLITHMB1.webp").exists()
        assert not (thumbs_root / "h240" / "CLITHMB1.webp").exists()

        second_result = runner.invoke(
            app,
            [
                "derive",
                "asset-thumbnails",
                "--rendition",
                "h120",
                "--rendition",
                "q200",
                "--force",
            ],
        )
        assert second_result.exit_code == 0
        assert "updated:" in second_result.stdout
    finally:
        get_settings.cache_clear()
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def _insert_photo_asset(
    *,
    runtime,
    short_id: str,
    source_type: str,
    external_id: str,
) -> None:
    with runtime.session_factory() as session:
        source = Source(
            name=f"{source_type}-{short_id}",
            type=source_type,
            external_id=f"{source_type}:{short_id}",
            config={},
        )
        session.add(source)
        session.flush()
        session.add(
            Asset(
                short_id=short_id,
                source_id=source.id,
                external_id=external_id,
                media_type="photo",
                timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                summary=None,
                latitude=None,
                longitude=None,
                metadata_json={},
            )
        )
        session.commit()

    with runtime.session_factory() as session:
        persisted = session.execute(
            select(Asset).where(Asset.short_id == short_id)
        ).scalar_one()
        assert persisted.short_id == short_id


def _copy_fixture_image(*, workspace_root: Path, fixture_name: str) -> Path:
    fixture_path = Path("test") / "assets" / fixture_name
    destination_path = workspace_root / "photos" / fixture_name
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(fixture_path, destination_path)
    return destination_path.resolve()


def _create_workspace_dir(*, prefix: str) -> Path:
    workspace_root = Path("var") / f"{prefix}-{uuid4().hex}"
    workspace_root.mkdir(parents=True, exist_ok=False)
    return workspace_root
