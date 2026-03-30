"""Asset thumbnail derive job tests."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from PIL import Image
from sqlalchemy import select

from pixelpast.analytics.asset_thumbnails import AssetThumbnailJob
from pixelpast.persistence.models import Asset, Source
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import Settings


def test_asset_thumbnail_job_generates_fixed_webp_renditions() -> None:
    workspace_root = _create_workspace_dir(prefix="asset-thumbnails-generate")
    runtime = None
    try:
        fixture_path = _copy_fixture_image(
            workspace_root=workspace_root,
            fixture_name="monalisa-1.jpg",
        )
        runtime = _create_runtime(workspace_root=workspace_root)
        _insert_photo_asset(
            runtime=runtime,
            short_id="PHOTO001",
            source_type="photos",
            external_id=fixture_path.as_posix(),
        )

        result = AssetThumbnailJob().run(runtime=runtime)

        assert result.status == "completed"
        assert result.asset_count == 1
        assert result.rendition_count == 3
        assert result.generated_count == 3
        assert result.overwritten_count == 0
        assert result.unchanged_count == 0
        assert result.skipped_count == 0
        assert result.failed_count == 0

        assert _read_image_size(_thumb_path(workspace_root, "h120", "PHOTO001")) == (
            120,
            120,
        )
        assert _read_image_size(_thumb_path(workspace_root, "h240", "PHOTO001")) == (
            240,
            240,
        )
        assert _read_image_size(_thumb_path(workspace_root, "q200", "PHOTO001")) == (
            200,
            200,
        )
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_asset_thumbnail_job_supports_lightroom_file_path_resolution() -> None:
    workspace_root = _create_workspace_dir(prefix="asset-thumbnails-lightroom")
    runtime = None
    try:
        fixture_path = _copy_fixture_image(
            workspace_root=workspace_root,
            fixture_name="monalisa-2.jpg",
        )
        runtime = _create_runtime(workspace_root=workspace_root)
        _insert_photo_asset(
            runtime=runtime,
            short_id="LIGHT001",
            source_type="lightroom_catalog",
            external_id="4E7C6031A061CE51AF186FE5022D4BFB",
            metadata_json={"file_path": fixture_path.as_posix()},
        )

        result = AssetThumbnailJob().run(
            runtime=runtime,
            renditions=("h120",),
        )

        assert result.status == "completed"
        assert result.generated_count == 1
        assert _read_image_size(_thumb_path(workspace_root, "h120", "LIGHT001")) == (
            120,
            120,
        )
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_asset_thumbnail_job_missing_only_and_force_rebuild_behave_deterministically(
) -> None:
    workspace_root = _create_workspace_dir(prefix="asset-thumbnails-force")
    runtime = None
    try:
        fixture_path = _copy_fixture_image(
            workspace_root=workspace_root,
            fixture_name="monalisa-3.jpg",
        )
        runtime = _create_runtime(workspace_root=workspace_root)
        _insert_photo_asset(
            runtime=runtime,
            short_id="FORCE001",
            source_type="photos",
            external_id=fixture_path.as_posix(),
        )

        first_result = AssetThumbnailJob().run(
            runtime=runtime,
            renditions=("h120", "q200"),
        )
        assert first_result.generated_count == 2

        corrupted_path = _thumb_path(workspace_root, "h120", "FORCE001")
        corrupted_path.write_bytes(b"corrupt-webp")

        second_result = AssetThumbnailJob().run(
            runtime=runtime,
            renditions=("h120", "q200"),
        )
        assert second_result.generated_count == 0
        assert second_result.unchanged_count == 2
        assert corrupted_path.read_bytes() == b"corrupt-webp"

        third_result = AssetThumbnailJob().run(
            runtime=runtime,
            renditions=("h120", "q200"),
            force=True,
        )
        assert third_result.generated_count == 0
        assert third_result.overwritten_count == 2
        assert _read_image_size(corrupted_path) == (120, 120)
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_asset_thumbnail_job_applies_wide_crop_rules() -> None:
    workspace_root = _create_workspace_dir(prefix="asset-thumbnails-wide")
    runtime = None
    try:
        wide_image_path = workspace_root / "photos" / "wide.jpg"
        wide_image_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (900, 100), color=(255, 0, 0)).save(wide_image_path)

        runtime = _create_runtime(workspace_root=workspace_root)
        _insert_photo_asset(
            runtime=runtime,
            short_id="WIDE0001",
            source_type="photos",
            external_id=wide_image_path.as_posix(),
        )

        result = AssetThumbnailJob().run(runtime=runtime)

        assert result.status == "completed"
        assert _read_image_size(_thumb_path(workspace_root, "h120", "WIDE0001")) == (
            360,
            120,
        )
        assert _read_image_size(_thumb_path(workspace_root, "h240", "WIDE0001")) == (
            720,
            240,
        )
        assert _read_image_size(_thumb_path(workspace_root, "q200", "WIDE0001")) == (
            200,
            200,
        )
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_asset_thumbnail_job_reports_skipped_and_failed_outputs() -> None:
    workspace_root = _create_workspace_dir(prefix="asset-thumbnails-skip-fail")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        missing_path = workspace_root / "photos" / "missing.jpg"
        unreadable_path = workspace_root / "photos" / "broken.jpg"
        unreadable_path.parent.mkdir(parents=True, exist_ok=True)
        unreadable_path.write_bytes(b"not-an-image")

        _insert_photo_asset(
            runtime=runtime,
            short_id="MISS0001",
            source_type="photos",
            external_id=missing_path.as_posix(),
        )
        _insert_photo_asset(
            runtime=runtime,
            short_id="UNSP0001",
            source_type="spotify",
            external_id="spotify:track:1",
        )
        _insert_photo_asset(
            runtime=runtime,
            short_id="FAIL0001",
            source_type="photos",
            external_id=unreadable_path.as_posix(),
        )

        result = AssetThumbnailJob().run(
            runtime=runtime,
            renditions=("h120",),
        )

        assert result.status == "partial_failure"
        assert result.asset_count == 3
        assert result.generated_count == 0
        assert result.overwritten_count == 0
        assert result.unchanged_count == 0
        assert result.skipped_count == 2
        assert result.failed_count == 1
        assert any(
            "Skipping thumbnail generation for asset MISS0001" in msg
            for msg in result.warning_messages
        )
        assert any("source type 'spotify'" in msg for msg in result.warning_messages)
        assert any(
            "Unsupported or unreadable image source" in msg
            for msg in result.warning_messages
        )
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def _create_runtime(*, workspace_root: Path):
    database_path = workspace_root / "pixelpast.db"
    settings = Settings(
        database_url=f"sqlite:///{database_path.as_posix()}",
        media_thumb_root=workspace_root / "thumbs",
    )
    runtime = create_runtime_context(settings=settings)
    initialize_database(runtime)
    return runtime


def _insert_photo_asset(
    *,
    runtime,
    short_id: str,
    source_type: str,
    external_id: str,
    metadata_json: dict[str, str] | None = None,
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
                metadata_json=metadata_json,
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


def _thumb_path(workspace_root: Path, rendition: str, short_id: str) -> Path:
    return workspace_root / "thumbs" / rendition / f"{short_id}.webp"


def _read_image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return image.size


def _create_workspace_dir(*, prefix: str) -> Path:
    workspace_root = Path("var") / f"{prefix}-{uuid4().hex}"
    workspace_root.mkdir(parents=True, exist_ok=False)
    return workspace_root
