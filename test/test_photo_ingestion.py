"""Photo ingestion connector and service tests."""

from __future__ import annotations

import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from pixelpast.ingestion.photos import (
    PhotoAssetCandidate,
    PhotoConnector,
    PhotoDiscoveryError,
    PhotoDiscoveryResult,
    PhotoExifMetadata,
    PhotoIngestionService,
)
from pixelpast.persistence.models import Asset, ImportRun, Source
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import Settings


def test_photo_ingestion_prefers_exif_timestamp_and_coordinates(monkeypatch) -> None:
    workspace_root = _create_workspace_dir(prefix="photo-exif")
    runtime = None
    try:
        photos_root = workspace_root / "photos"
        photo_path = photos_root / "trip" / "photo.jpg"
        photo_path.parent.mkdir(parents=True)
        photo_path.write_bytes(b"not-a-real-image")
        os.utime(photo_path, (1_700_000_000, 1_700_000_000))

        expected_timestamp = datetime(2022, 5, 4, 3, 2, 1, tzinfo=UTC)
        monkeypatch.setattr(
            "pixelpast.ingestion.photos.connector.extract_photo_exif_metadata",
            lambda path: PhotoExifMetadata(
                timestamp=expected_timestamp,
                latitude=48.137154,
                longitude=11.576124,
            ),
        )

        runtime = _create_runtime(
            workspace_root=workspace_root,
            photos_root=photos_root,
        )
        result = PhotoIngestionService().ingest(runtime=runtime)
        assert result.processed_asset_count == 1
        assert result.error_count == 0
        assert result.status == "completed"

        with runtime.session_factory() as session:
            asset = session.execute(select(Asset)).scalar_one()

        assert asset.timestamp == expected_timestamp
        assert asset.latitude == 48.137154
        assert asset.longitude == 11.576124
        assert asset.external_id == photo_path.resolve().as_posix()
        assert asset.metadata_json == {}
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_photo_ingestion_is_idempotent_and_records_import_runs(
) -> None:
    workspace_root = _create_workspace_dir(prefix="photo-idempotent")
    runtime = None
    try:
        photos_root = workspace_root / "photos"
        photos_root.mkdir()

        timestamped_photo = photos_root / "album" / "IMG_20240102_030405.jpg"
        timestamped_photo.parent.mkdir()
        timestamped_photo.write_bytes(b"not-a-real-image")

        fallback_photo = photos_root / "album" / "scan.png"
        fallback_photo.write_bytes(b"not-a-real-image")
        os.utime(fallback_photo, (1_710_000_000, 1_710_000_000))

        runtime = _create_runtime(
            workspace_root=workspace_root,
            photos_root=photos_root,
        )
        first_result = PhotoIngestionService().ingest(runtime=runtime)
        second_result = PhotoIngestionService().ingest(runtime=runtime)

        assert first_result.processed_asset_count == 2
        assert second_result.processed_asset_count == 2
        assert first_result.status == "completed"
        assert second_result.status == "completed"

        with runtime.session_factory() as session:
            assets = session.execute(
                select(Asset).order_by(Asset.external_id)
            ).scalars()
            assets = list(assets)
            import_runs = session.execute(
                select(ImportRun).order_by(ImportRun.id)
            ).scalars()
            import_runs = list(import_runs)
            sources = session.execute(select(Source)).scalars()
            sources = list(sources)

        assert len(assets) == 2
        assert len(import_runs) == 2
        assert len(sources) == 1
        assert [run.status for run in import_runs] == ["completed", "completed"]
        assert all(run.mode == "full" for run in import_runs)
        assert sources[0].config == {"root_path": photos_root.resolve().as_posix()}

        assets_by_name = {Path(asset.external_id).name: asset for asset in assets}
        assert assets_by_name["IMG_20240102_030405.jpg"].timestamp == datetime(
            2024,
            1,
            2,
            3,
            4,
            5,
            tzinfo=UTC,
        )
        assert assets_by_name["IMG_20240102_030405.jpg"].metadata_json == {}
        assert assets_by_name["scan.png"].timestamp == datetime.fromtimestamp(
            1_710_000_000,
            tz=UTC,
        )
        assert assets_by_name["scan.png"].metadata_json == {}
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_photo_ingestion_handles_empty_directories() -> None:
    workspace_root = _create_workspace_dir(prefix="photo-empty")
    runtime = None
    try:
        photos_root = workspace_root / "photos"
        photos_root.mkdir()

        runtime = _create_runtime(
            workspace_root=workspace_root,
            photos_root=photos_root,
        )
        result = PhotoIngestionService().ingest(runtime=runtime)

        assert result.processed_asset_count == 0
        assert result.error_count == 0
        assert result.status == "completed"

        with runtime.session_factory() as session:
            assets = list(session.execute(select(Asset)).scalars())
            import_runs = list(session.execute(select(ImportRun)).scalars())

        assert assets == []
        assert len(import_runs) == 1
        assert import_runs[0].status == "completed"
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_photo_connector_partial_failure_is_reported_and_persisted(
) -> None:
    workspace_root = _create_workspace_dir(prefix="photo-partial")
    runtime = None
    try:
        photos_root = workspace_root / "photos"
        photos_root.mkdir()

        runtime = _create_runtime(
            workspace_root=workspace_root,
            photos_root=photos_root,
        )
        result = PhotoIngestionService(connector=_PartialFailureConnector()).ingest(
            runtime=runtime
        )

        assert result.processed_asset_count == 1
        assert result.error_count == 1
        assert result.status == "partial_failure"

        with runtime.session_factory() as session:
            assets = list(session.execute(select(Asset)).scalars())
            import_run = session.execute(select(ImportRun)).scalar_one()

        assert len(assets) == 1
        assert import_run.status == "partial_failure"
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_photo_connector_builds_filename_and_mtime_fallbacks() -> None:
    workspace_root = _create_workspace_dir(prefix="photo-fallbacks")
    try:
        photos_root = workspace_root / "photos"
        photos_root.mkdir()

        connector = PhotoConnector()

        filename_photo = photos_root / "IMG_20230304_050607.jpeg"
        filename_photo.write_bytes(b"photo")
        filename_candidate = connector.build_asset_candidate(
            root=photos_root,
            path=filename_photo,
        )

        mtime_photo = photos_root / "plain.heic"
        mtime_photo.write_bytes(b"photo")
        os.utime(mtime_photo, (1_720_000_000, 1_720_000_000))
        mtime_candidate = connector.build_asset_candidate(
            root=photos_root,
            path=mtime_photo,
        )

        assert filename_candidate.timestamp == datetime(2023, 3, 4, 5, 6, 7, tzinfo=UTC)
        assert filename_candidate.metadata_json == {}
        assert mtime_candidate.timestamp == datetime.fromtimestamp(
            1_720_000_000,
            tz=UTC,
        )
        assert mtime_candidate.metadata_json == {}
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


class _PartialFailureConnector(PhotoConnector):
    """Test connector that simulates one successful asset and one failure."""

    def discover(self, root: Path) -> PhotoDiscoveryResult:
        candidate = PhotoAssetCandidate(
            external_id=(root / "ok.jpg").resolve().as_posix(),
            media_type="photo",
            timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
            latitude=None,
            longitude=None,
            metadata_json={},
        )
        return PhotoDiscoveryResult(
            assets=[candidate],
            errors=[
                PhotoDiscoveryError(
                    path=root / "broken.jpg",
                    message="decode error",
                )
            ],
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
