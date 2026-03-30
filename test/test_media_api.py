"""Integration tests for media delivery routes."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from PIL import Image

from pixelpast.analytics.asset_thumbnails.rendering import render_thumbnail
from pixelpast.api.app import create_app
from pixelpast.persistence.models import Asset, Source
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import Settings


def test_thumbnail_media_cache_hit_is_served_without_asset_lookup() -> None:
    workspace_root = _create_workspace_dir(prefix="media-api-cache-hit")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        fixture_path = _copy_fixture_image(
            workspace_root=workspace_root,
            fixture_name="monalisa-1.jpg",
        )
        output_path = workspace_root / "thumbs" / "h120" / "CACHE001.webp"
        render_thumbnail(
            source_path=fixture_path,
            output_path=output_path,
            rendition="h120",
        )

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get("/media/h120/CACHE001.webp")

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/webp"
        assert response.content == output_path.read_bytes()
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_thumbnail_media_cache_miss_generates_and_persists_requested_rendition(
) -> None:
    workspace_root = _create_workspace_dir(prefix="media-api-lazy-generate")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        fixture_path = _copy_fixture_image(
            workspace_root=workspace_root,
            fixture_name="monalisa-2.jpg",
        )
        _insert_photo_asset(
            runtime=runtime,
            short_id="PHOTO001",
            source_type="photos",
            external_id=fixture_path.as_posix(),
        )

        app = create_app(settings=runtime.settings)
        output_path = workspace_root / "thumbs" / "h240" / "PHOTO001.webp"
        assert not output_path.exists()

        with TestClient(app) as client:
            response = client.get("/media/h240/PHOTO001.webp")

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/webp"
        assert output_path.exists()
        assert response.content == output_path.read_bytes()
        assert _read_image_size(output_path) == (240, 240)
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_thumbnail_media_rejects_unknown_short_ids() -> None:
    workspace_root = _create_workspace_dir(prefix="media-api-unknown")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        app = create_app(settings=runtime.settings)

        with TestClient(app) as client:
            response = client.get("/media/q200/MISS0001.webp")

        assert response.status_code == 404
        assert response.json() == {"detail": "asset short id 'MISS0001' does not exist"}
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_thumbnail_media_rejects_assets_without_supported_original_path() -> None:
    workspace_root = _create_workspace_dir(prefix="media-api-unsupported")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        _insert_photo_asset(
            runtime=runtime,
            short_id="TRACK001",
            source_type="spotify",
            external_id="spotify:track:1",
        )
        app = create_app(settings=runtime.settings)

        with TestClient(app) as client:
            response = client.get("/media/h120/TRACK001.webp")

        assert response.status_code == 415
        assert response.json() == {
            "detail": "asset 'TRACK001' does not support image thumbnails"
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_thumbnail_media_reports_missing_original_files() -> None:
    workspace_root = _create_workspace_dir(prefix="media-api-missing-original")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        missing_path = workspace_root / "photos" / "missing.jpg"
        _insert_photo_asset(
            runtime=runtime,
            short_id="PHOTO404",
            source_type="photos",
            external_id=missing_path.as_posix(),
        )
        app = create_app(settings=runtime.settings)

        with TestClient(app) as client:
            response = client.get("/media/h120/PHOTO404.webp")

        assert response.status_code == 404
        assert response.json() == {
            "detail": "original file for asset 'PHOTO404' is missing"
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_original_media_serves_photo_with_inline_content_disposition() -> None:
    workspace_root = _create_workspace_dir(prefix="media-api-original-photo")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        fixture_path = _copy_fixture_image(
            workspace_root=workspace_root,
            fixture_name="monalisa-1.jpg",
        )
        _insert_photo_asset(
            runtime=runtime,
            short_id="ORIG0001",
            source_type="photos",
            external_id=fixture_path.as_posix(),
            metadata_json={"source_path": fixture_path.as_posix()},
        )
        app = create_app(settings=runtime.settings)

        with TestClient(app) as client:
            response = client.get("/media/orig/ORIG0001")

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
        assert (
            response.headers["content-disposition"]
            == 'inline; filename="monalisa-1.jpg"'
        )
        assert response.content == fixture_path.read_bytes()
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_original_media_prefers_preserved_lightroom_filename() -> None:
    workspace_root = _create_workspace_dir(prefix="media-api-original-lightroom")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        fixture_path = _copy_fixture_image(
            workspace_root=workspace_root,
            fixture_name="monalisa-2.jpg",
        )
        _insert_photo_asset(
            runtime=runtime,
            short_id="LRCAT001",
            source_type="lightroom_catalog",
            external_id="xmp:document:id",
            metadata_json={
                "file_path": fixture_path.as_posix(),
                "file_name": "renamed-monalisa-2.jpg",
                "preserved_file_name": "monalisa-2.jpg",
            },
        )
        app = create_app(settings=runtime.settings)

        with TestClient(app) as client:
            response = client.get("/media/orig/LRCAT001")

        assert response.status_code == 200
        assert (
            response.headers["content-disposition"]
            == 'inline; filename="monalisa-2.jpg"'
        )
        assert response.content == fixture_path.read_bytes()
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_original_media_rejects_unknown_short_ids() -> None:
    workspace_root = _create_workspace_dir(prefix="media-api-original-unknown")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        app = create_app(settings=runtime.settings)

        with TestClient(app) as client:
            response = client.get("/media/orig/MISS0001")

        assert response.status_code == 404
        assert response.json() == {"detail": "asset short id 'MISS0001' does not exist"}
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_original_media_rejects_assets_without_resolvable_original_path() -> None:
    workspace_root = _create_workspace_dir(prefix="media-api-original-unresolved")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        _insert_photo_asset(
            runtime=runtime,
            short_id="BROKEN01",
            source_type="spotify",
            external_id="spotify:track:1",
        )
        app = create_app(settings=runtime.settings)

        with TestClient(app) as client:
            response = client.get("/media/orig/BROKEN01")

        assert response.status_code == 404
        assert response.json() == {
            "detail": "original file path for asset 'BROKEN01' could not be resolved"
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_original_media_reports_missing_original_files() -> None:
    workspace_root = _create_workspace_dir(prefix="media-api-original-missing")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        missing_path = workspace_root / "photos" / "missing.jpg"
        _insert_photo_asset(
            runtime=runtime,
            short_id="ORIG4040",
            source_type="photos",
            external_id=missing_path.as_posix(),
            metadata_json={"source_path": missing_path.as_posix()},
        )
        app = create_app(settings=runtime.settings)

        with TestClient(app) as client:
            response = client.get("/media/orig/ORIG4040")

        assert response.status_code == 404
        assert response.json() == {
            "detail": "original file for asset 'ORIG4040' is missing"
        }
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


def _copy_fixture_image(*, workspace_root: Path, fixture_name: str) -> Path:
    fixture_path = Path("test") / "assets" / fixture_name
    destination_path = workspace_root / "photos" / fixture_name
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(fixture_path, destination_path)
    return destination_path.resolve()


def _read_image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return image.size


def _create_workspace_dir(*, prefix: str) -> Path:
    workspace_root = Path("var") / f"{prefix}-{uuid4().hex}"
    workspace_root.mkdir(parents=True, exist_ok=False)
    return workspace_root
