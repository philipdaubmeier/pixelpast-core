"""Tests for Lightroom catalog discovery and read-only SQLite loading."""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest

from pixelpast.ingestion.lightroom_catalog import (
    LoadedLightroomCatalog,
    LightroomCatalogConnector,
    LightroomCatalogDescriptor,
    LightroomCatalogDiscoverer,
    LightroomCatalogFetcher,
    LightroomCatalogLoadProgress,
    LightroomChosenImageRow,
    LightroomCollectionRow,
    LightroomFaceRow,
    open_lightroom_catalog_read_only,
)

_FIXTURE_PATH = Path("test/assets/lightroom-classic-catalog-test-fixture.lrcat").resolve()


def test_lightroom_catalog_discovery_accepts_single_supported_catalog_file() -> None:
    workspace_root = _build_test_workspace("lightroom-discovery-file")

    try:
        catalog_path = workspace_root / "fixture-copy.lrcat"
        shutil.copyfile(_FIXTURE_PATH, catalog_path)
        configured_path = catalog_path

        discovered_labels: list[str] = []
        discovered = LightroomCatalogDiscoverer().discover_catalogs(
            configured_path,
            on_catalog_discovered=lambda descriptor, count: discovered_labels.append(
                f"{count}:{descriptor.origin_label}"
            ),
        )

        assert discovered == (
            LightroomCatalogDescriptor(
                path=catalog_path.resolve(),
                configured_path=configured_path,
            ),
        )
        assert discovered[0].original_configured_path == configured_path
        assert discovered[0].file_extension == ".lrcat"
        assert discovered_labels == [f"1:{catalog_path.resolve().as_posix()}"]
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_lightroom_catalog_discovery_accepts_sqlite_extension_and_rejects_invalid_roots(
) -> None:
    workspace_root = _build_test_workspace("lightroom-discovery-invalid")

    try:
        sqlite_catalog_path = workspace_root / "fixture-copy.sqlite"
        shutil.copyfile(_FIXTURE_PATH, sqlite_catalog_path)
        unsupported_path = workspace_root / "fixture-copy.txt"
        unsupported_path.write_text("not a catalog", encoding="utf-8")
        directory_path = workspace_root / "catalog-dir"
        directory_path.mkdir()
        missing_path = workspace_root / "missing.lrcat"

        discoverer = LightroomCatalogDiscoverer()

        discovered = discoverer.discover_catalogs(sqlite_catalog_path)
        assert discovered[0].file_extension == ".sqlite"

        with pytest.raises(ValueError, match="does not exist"):
            discoverer.discover_catalogs(missing_path)
        with pytest.raises(ValueError, match="must be a file, not a directory"):
            discoverer.discover_catalogs(directory_path)
        with pytest.raises(ValueError, match="supported extensions"):
            discoverer.discover_catalogs(unsupported_path)
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_lightroom_catalog_fetcher_loads_chosen_images_faces_and_collection_rows(
) -> None:
    descriptor = LightroomCatalogDescriptor(path=_FIXTURE_PATH)
    progress_events: list[LightroomCatalogLoadProgress] = []

    loaded_catalogs = LightroomCatalogFetcher().fetch_catalogs(
        catalogs=(descriptor,),
        on_catalog_progress=progress_events.append,
    )

    assert loaded_catalogs == (
        LoadedLightroomCatalog(
            descriptor=descriptor,
            chosen_images=(
                LightroomChosenImageRow(
                    image_id=67,
                    root_file_id=71,
                    file_name="monalisa-1.jpg",
                    file_path=(
                        "C:/Users/phili/Desktop/Source/pixelpast-core/test/assets/"
                        "monalisa-1.jpg"
                    ),
                    capture_time_text="2020-01-01T02:03:40.000",
                    rating=3,
                    color_label="Rot",
                    xmp_blob=loaded_catalogs[0].chosen_images[0].xmp_blob,
                    caption=None,
                    creator_name="Leonardo da Vinci",
                    gps_latitude=48.86189241666667,
                    gps_longitude=2.3358866333333332,
                ),
                LightroomChosenImageRow(
                    image_id=68,
                    root_file_id=118,
                    file_name="monalisa-2.jpg",
                    file_path=(
                        "C:/Users/phili/Desktop/Source/pixelpast-core/test/assets/"
                        "monalisa-2.jpg"
                    ),
                    capture_time_text="2020-01-01T02:03:40.000",
                    rating=4,
                    color_label="Gelb",
                    xmp_blob=loaded_catalogs[0].chosen_images[1].xmp_blob,
                    caption=None,
                    creator_name="Leonardo da Vinci",
                    gps_latitude=48.86039605,
                    gps_longitude=2.334584866666667,
                ),
                LightroomChosenImageRow(
                    image_id=69,
                    root_file_id=174,
                    file_name="monalisa-3.jpg",
                    file_path=(
                        "C:/Users/phili/Desktop/Source/pixelpast-core/test/assets/"
                        "monalisa-3.jpg"
                    ),
                    capture_time_text="2020-01-01T02:03:40.000",
                    rating=5,
                    color_label="Grün",
                    xmp_blob=loaded_catalogs[0].chosen_images[2].xmp_blob,
                    caption=None,
                    creator_name="Leonardo da Vinci",
                    gps_latitude=48.860383066666664,
                    gps_longitude=2.3385617666666665,
                ),
            ),
            face_rows=(
                LightroomFaceRow(
                    image_id=67,
                    face_id=103,
                    name="Mona Lisa",
                    left=0.29167,
                    top=0.25980499999999995,
                    right=0.58579,
                    bottom=0.537995,
                    region_type=1.0,
                    orientation=0.0,
                ),
                LightroomFaceRow(
                    image_id=68,
                    face_id=156,
                    name="Mona Lisa",
                    left=0.10048499999999999,
                    top=0.09559,
                    right=0.348035,
                    bottom=0.33701,
                    region_type=1.0,
                    orientation=0.0,
                ),
                LightroomFaceRow(
                    image_id=68,
                    face_id=159,
                    name="John Doe",
                    left=0.486525,
                    top=0.460785,
                    right=0.814955,
                    bottom=0.8063750000000001,
                    region_type=1.0,
                    orientation=0.0,
                ),
                LightroomFaceRow(
                    image_id=69,
                    face_id=200,
                    name="John Doe",
                    left=0.319855,
                    top=0.23038999999999998,
                    right=0.6299049999999999,
                    bottom=0.54657,
                    region_type=1.0,
                    orientation=0.0,
                ),
                LightroomFaceRow(
                    image_id=69,
                    face_id=203,
                    name="John Doe",
                    left=0.09681499999999998,
                    top=0.609065,
                    right=0.348045,
                    bottom=0.924015,
                    region_type=1.0,
                    orientation=0.0,
                ),
                LightroomFaceRow(
                    image_id=69,
                    face_id=206,
                    name="Mona Lisa",
                    left=0.585785,
                    top=0.6200950000000001,
                    right=0.841915,
                    bottom=0.835785,
                    region_type=1.0,
                    orientation=0.0,
                ),
            ),
            collection_rows=(),
        ),
    )
    assert progress_events == [
        LightroomCatalogLoadProgress(
            event="submitted",
            catalog=descriptor,
            catalog_index=1,
            catalog_total=1,
        ),
        LightroomCatalogLoadProgress(
            event="completed",
            catalog=descriptor,
            catalog_index=1,
            catalog_total=1,
        ),
    ]


def test_lightroom_catalog_open_read_only_rejects_schema_writes() -> None:
    workspace_root = _build_test_workspace("lightroom-read-only")

    try:
        catalog_path = workspace_root / "fixture-copy.lrcat"
        shutil.copyfile(_FIXTURE_PATH, catalog_path)

        with open_lightroom_catalog_read_only(catalog_path) as connection:
            with pytest.raises(
                sqlite3.OperationalError,
                match="readonly|read-only|attempt to write",
            ):
                connection.execute("CREATE TABLE codex_probe (id INTEGER PRIMARY KEY)")
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_lightroom_catalog_connector_delegates_discovery_and_raw_load() -> None:
    workspace_root = _build_test_workspace("lightroom-connector")

    try:
        catalog_path = workspace_root / "fixture-copy.lrcat"
        shutil.copyfile(_FIXTURE_PATH, catalog_path)

        connector = LightroomCatalogConnector()
        discovered = connector.discover_catalogs(catalog_path)
        loaded = connector.fetch_catalogs(catalogs=discovered)

        assert discovered == (
            LightroomCatalogDescriptor(
                path=catalog_path.resolve(),
                configured_path=catalog_path,
            ),
        )
        assert len(loaded) == 1
        assert loaded[0].descriptor == discovered[0]
        assert [row.image_id for row in loaded[0].chosen_images] == [67, 68, 69]
        assert [row.face_id for row in loaded[0].face_rows] == [
            103,
            156,
            159,
            200,
            203,
            206,
        ]
        assert loaded[0].collection_rows == ()
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def _build_test_workspace(prefix: str) -> Path:
    workspace_root = Path("var") / f"{prefix}-{uuid4().hex}"
    workspace_root.mkdir(parents=True, exist_ok=False)
    return workspace_root
