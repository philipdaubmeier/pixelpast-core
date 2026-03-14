"""Characterization tests for public photo ingestion contracts."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from pixelpast.ingestion.photos import (
    PhotoAssetCandidate,
    PhotoConnector,
    PhotoDiscoveryError,
    PhotoDiscoveryResult,
    PhotoIngestionProgressSnapshot,
    PhotoIngestionResult,
    PhotoIngestionService,
    PhotoMetadataBatchProgress,
    PhotoPersonCandidate,
)
from pixelpast.ingestion.photos import contracts as photo_contracts
from pixelpast.ingestion.photos import progress as photo_progress
from pixelpast.ingestion.photos.connector import PhotoConnector as ConnectorModulePhotoConnector
from pixelpast.ingestion.photos.connector import (
    PhotoAssetCandidate as ConnectorModulePhotoAssetCandidate,
)
from pixelpast.ingestion.photos.connector import (
    PhotoDiscoveryError as ConnectorModulePhotoDiscoveryError,
)
from pixelpast.ingestion.photos.connector import (
    PhotoDiscoveryResult as ConnectorModulePhotoDiscoveryResult,
)
from pixelpast.ingestion.photos.connector import (
    PhotoMetadataBatchProgress as ConnectorModulePhotoMetadataBatchProgress,
)
from pixelpast.ingestion.photos.connector import (
    PhotoPersonCandidate as ConnectorModulePhotoPersonCandidate,
)
from pixelpast.ingestion.photos.service import (
    PhotoIngestionProgressSnapshot as ServiceModulePhotoIngestionProgressSnapshot,
)
from pixelpast.ingestion.photos.service import (
    PhotoIngestionResult as ServiceModulePhotoIngestionResult,
)
from pixelpast.ingestion.photos.persist import _resolve_persistence_outcome
from pixelpast.persistence.models import Asset
from pixelpast.persistence.repositories import AssetRepository, AssetUpsertResult
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import Settings


def test_photo_ingest_public_contract_imports_remain_stable() -> None:
    assert PhotoAssetCandidate is photo_contracts.PhotoAssetCandidate
    assert PhotoAssetCandidate is ConnectorModulePhotoAssetCandidate
    assert PhotoPersonCandidate is photo_contracts.PhotoPersonCandidate
    assert PhotoPersonCandidate is ConnectorModulePhotoPersonCandidate
    assert PhotoDiscoveryError is photo_contracts.PhotoDiscoveryError
    assert PhotoDiscoveryError is ConnectorModulePhotoDiscoveryError
    assert PhotoDiscoveryResult is photo_contracts.PhotoDiscoveryResult
    assert PhotoDiscoveryResult is ConnectorModulePhotoDiscoveryResult
    assert PhotoMetadataBatchProgress is photo_contracts.PhotoMetadataBatchProgress
    assert PhotoMetadataBatchProgress is ConnectorModulePhotoMetadataBatchProgress
    assert PhotoIngestionResult is photo_contracts.PhotoIngestionResult
    assert PhotoIngestionResult is ServiceModulePhotoIngestionResult
    assert PhotoIngestionProgressSnapshot is photo_contracts.PhotoIngestionProgressSnapshot
    assert (
        PhotoIngestionProgressSnapshot
        is ServiceModulePhotoIngestionProgressSnapshot
    )
    assert PhotoIngestionProgressSnapshot is photo_progress.PhotoIngestionProgressSnapshot
    assert PhotoConnector is ConnectorModulePhotoConnector


def test_photo_ingestion_emits_stable_progress_event_names_and_batch_counters() -> None:
    workspace_root = _create_workspace_dir(prefix="photo-contract-progress")
    runtime = None
    try:
        photos_root = workspace_root / "photos"
        photos_root.mkdir()
        for name in ("first.jpg", "second.jpg"):
            (photos_root / name).write_bytes(b"photo")

        runtime = _create_runtime(
            workspace_root=workspace_root,
            photos_root=photos_root,
        )
        snapshots: list[PhotoIngestionProgressSnapshot] = []

        result = PhotoIngestionService(
            connector=_ContractConnector(),
        ).ingest(
            runtime=runtime,
            progress_callback=snapshots.append,
        )

        assert result.status == "completed"
        assert result.inserted_asset_count == 2

        events = [snapshot.event for snapshot in snapshots]
        assert "phase_started" in events
        assert "phase_completed" in events
        assert "metadata_batch_submitted" in events
        assert "metadata_batch_completed" in events
        assert events[-1] == "run_finished"

        submitted_snapshot = next(
            snapshot
            for snapshot in snapshots
            if snapshot.event == "metadata_batch_submitted"
        )
        assert submitted_snapshot.metadata_batches_submitted == 1
        assert submitted_snapshot.metadata_batches_completed == 0
        assert submitted_snapshot.current_batch_index == 1
        assert submitted_snapshot.current_batch_total == 1
        assert submitted_snapshot.current_batch_size == 2

        completed_snapshot = next(
            snapshot
            for snapshot in snapshots
            if snapshot.event == "metadata_batch_completed"
        )
        assert completed_snapshot.metadata_batches_submitted == 1
        assert completed_snapshot.metadata_batches_completed == 1
        assert completed_snapshot.current_batch_index == 1
        assert completed_snapshot.current_batch_total == 1
        assert completed_snapshot.current_batch_size == 2

        finished_snapshot = snapshots[-1]
        assert finished_snapshot.phase == "finalization"
        assert finished_snapshot.status == "completed"
        assert finished_snapshot.phase_status == "completed"
        assert finished_snapshot.items_persisted == 2
        assert finished_snapshot.inserted_item_count == 2
        assert finished_snapshot.updated_item_count == 0
        assert finished_snapshot.unchanged_item_count == 0
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_photo_ingestion_emits_run_failed_event_for_terminal_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_root = _create_workspace_dir(prefix="photo-contract-failed")
    runtime = None
    try:
        photos_root = workspace_root / "photos"
        photos_root.mkdir()
        (photos_root / "image.jpg").write_bytes(b"photo")

        runtime = _create_runtime(
            workspace_root=workspace_root,
            photos_root=photos_root,
        )
        snapshots: list[PhotoIngestionProgressSnapshot] = []

        def fail_upsert(self, **kwargs):
            del self, kwargs
            raise RuntimeError("forced persistence failure")

        monkeypatch.setattr(AssetRepository, "upsert", fail_upsert)

        with pytest.raises(RuntimeError, match="forced persistence failure"):
            PhotoIngestionService(
                connector=_ContractConnector(),
            ).ingest(
                runtime=runtime,
                progress_callback=snapshots.append,
            )

        assert snapshots[-1].event == "run_failed"
        assert snapshots[-1].status == "failed"
        assert snapshots[-1].phase_status == "failed"
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_persistence_outcome_semantics_remain_inserted_updated_or_unchanged() -> None:
    asset = Asset(
        external_id="asset-1",
        media_type="photo",
        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        latitude=None,
        longitude=None,
        metadata_json={},
    )

    assert (
        _resolve_persistence_outcome(
            upsert_result=AssetUpsertResult(asset=asset, status="inserted"),
            tags_changed=False,
            people_changed=False,
        )
        == "inserted"
    )
    assert (
        _resolve_persistence_outcome(
            upsert_result=AssetUpsertResult(asset=asset, status="updated"),
            tags_changed=False,
            people_changed=False,
        )
        == "updated"
    )
    assert (
        _resolve_persistence_outcome(
            upsert_result=AssetUpsertResult(asset=asset, status="unchanged"),
            tags_changed=True,
            people_changed=False,
        )
        == "updated"
    )
    assert (
        _resolve_persistence_outcome(
            upsert_result=AssetUpsertResult(asset=asset, status="unchanged"),
            tags_changed=False,
            people_changed=True,
        )
        == "updated"
    )
    assert (
        _resolve_persistence_outcome(
            upsert_result=AssetUpsertResult(asset=asset, status="unchanged"),
            tags_changed=False,
            people_changed=False,
        )
        == "unchanged"
    )


class _ContractConnector(PhotoConnector):
    """Connector used to freeze public override-point behavior."""

    def discover_paths(
        self,
        root: Path,
        *,
        on_path_discovered=None,
    ) -> list[Path]:
        paths = [root / "first.jpg", root / "second.jpg"]
        if on_path_discovered is not None:
            for index, path in enumerate(paths, start=1):
                on_path_discovered(path, index)
        return paths

    def extract_metadata_by_path(self, *, paths: list[Path], on_batch_progress=None):
        if on_batch_progress is not None:
            on_batch_progress(
                PhotoMetadataBatchProgress(
                    event="submitted",
                    batch_index=1,
                    batch_total=1,
                    batch_size=len(paths),
                )
            )
        metadata = {path.resolve().as_posix(): {"SourceFile": path.as_posix()} for path in paths}
        if on_batch_progress is not None:
            on_batch_progress(
                PhotoMetadataBatchProgress(
                    event="completed",
                    batch_index=1,
                    batch_total=1,
                    batch_size=len(paths),
                )
            )
        return metadata

    def build_asset_candidate(
        self,
        *,
        root: Path,
        path: Path,
        metadata=None,
    ) -> PhotoAssetCandidate:
        del root, metadata
        return PhotoAssetCandidate(
            external_id=path.resolve().as_posix(),
            media_type="photo",
            timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
            summary=path.stem,
            latitude=None,
            longitude=None,
            creator_name=None,
            tag_paths=(),
            asset_tag_paths=(),
            persons=(),
            metadata_json={"name": path.name},
        )


def _create_runtime(*, workspace_root: Path, photos_root: Path):
    database_path = workspace_root / "pixelpast.db"
    settings = Settings(
        database_url=f"sqlite:///{database_path.as_posix()}",
        photos_root=photos_root,
    )
    runtime = create_runtime_context(settings=settings)
    initialize_database(runtime)
    return runtime


def _create_workspace_dir(*, prefix: str) -> Path:
    workspace_root = Path("var") / f"{prefix}-{uuid4().hex}"
    workspace_root.mkdir(parents=True, exist_ok=False)
    return workspace_root
