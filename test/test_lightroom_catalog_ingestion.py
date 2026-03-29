"""Integration tests for Lightroom staged ingestion and shared progress."""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select

from pixelpast.ingestion.lightroom_catalog import LightroomCatalogIngestionService
from pixelpast.persistence.models import Asset, JobRun, Source
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import Settings

_FIXTURE_PATH = Path("test/assets/lightroom-classic-catalog-test-fixture.lrcat").resolve()


def test_lightroom_catalog_ingestion_uses_staged_runner_and_persists_assets() -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    try:
        catalog_path = workspace_root / _FIXTURE_PATH.name
        shutil.copy2(_FIXTURE_PATH, catalog_path)

        result = LightroomCatalogIngestionService().ingest(
            runtime=runtime,
            root=catalog_path,
        )

        with runtime.session_factory() as session:
            assets = list(session.execute(select(Asset).order_by(Asset.id)).scalars())
            sources = list(session.execute(select(Source).order_by(Source.id)).scalars())
            job_run = session.execute(
                select(JobRun).order_by(JobRun.id.desc())
            ).scalar_one()

        assert result.status == "completed"
        assert result.processed_catalog_count == 1
        assert result.processed_asset_count == 3
        assert result.persisted_asset_count == 3
        assert result.error_count == 0
        assert len(assets) == 3
        assert len(sources) == 1
        assert sources[0].config == {"catalog_path": catalog_path.resolve().as_posix()}
        assert job_run.status == "completed"
        assert job_run.progress_json == {
            "total": 1,
            "completed": 1,
            "inserted": 3,
            "updated": 0,
            "unchanged": 0,
            "skipped": 0,
            "failed": 0,
            "missing_from_source": 0,
            "persisted_asset_count": 3,
        }
    finally:
        runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_lightroom_catalog_ingestion_reads_runtime_catalog_path_and_emits_progress() -> None:
    workspace_root = _create_workspace_root()
    runtime = None
    try:
        catalog_path = workspace_root / _FIXTURE_PATH.name
        shutil.copy2(_FIXTURE_PATH, catalog_path)
        runtime = _create_runtime(lightroom_catalog_path=catalog_path)
        snapshots = []

        result = LightroomCatalogIngestionService().ingest(
            runtime=runtime,
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
            and snapshot.phase == "filesystem discovery"
            and snapshot.completed == 1
            and snapshot.total == 1
            for snapshot in snapshots
        )
        assert any(
            snapshot.event == "progress"
            and snapshot.phase == "metadata extraction"
            and snapshot.completed == 1
            and snapshot.total == 1
            for snapshot in snapshots
        )
        assert any(
            snapshot.event == "progress"
            and snapshot.phase == "canonical persistence"
            and snapshot.completed == 1
            and snapshot.inserted == 3
            and snapshot.total == 1
            for snapshot in snapshots
        )
        assert snapshots[-1].event == "run_finished"
        assert snapshots[-1].phase == "finalization"
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_lightroom_catalog_ingestion_requires_configured_catalog_path() -> None:
    runtime = _create_runtime()
    try:
        with pytest.raises(
            ValueError,
            match="PIXELPAST_LIGHTROOM_CATALOG_PATH",
        ):
            LightroomCatalogIngestionService().ingest(runtime=runtime)
    finally:
        runtime.engine.dispose()


def _create_runtime(*, lightroom_catalog_path: Path | None = None):
    runtime = create_runtime_context(
        settings=Settings(
            database_url="sqlite://",
            lightroom_catalog_path=lightroom_catalog_path,
        )
    )
    initialize_database(runtime)
    return runtime


def _create_workspace_root() -> Path:
    workspace_root = Path("var") / f"lightroom-ingest-{uuid4().hex}"
    workspace_root.mkdir(parents=True, exist_ok=False)
    return workspace_root
