"""Integration tests for Lightroom staged ingestion and shared progress."""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select

from pixelpast.ingestion.lightroom_catalog import LightroomCatalogIngestionService
from pixelpast.persistence.models import (
    Asset,
    AssetPerson,
    AssetTag,
    JobRun,
    Person,
    Source,
    Tag,
)
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import Settings

_FIXTURE_PATH = Path("test/assets/lightroom-classic-catalog-test-fixture.lrcat").resolve()
_SECOND_ASSET_EXTERNAL_ID = "4E7C6031A061CE51AF186FE5022D4BFB"
_FIRST_ASSET_EXTERNAL_ID = "3EC1FA8A05CE57D59B0BA4C353580C5F"


def test_lightroom_catalog_ingestion_imports_fixture_end_to_end_without_schema_changes() -> (
    None
):
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    try:
        catalog_path = _copy_fixture_catalog(workspace_root)

        result = LightroomCatalogIngestionService().ingest(
            runtime=runtime,
            root=catalog_path,
        )

        with runtime.session_factory() as session:
            assets = list(
                session.execute(select(Asset).order_by(Asset.external_id)).scalars()
            )
            tags = list(session.execute(select(Tag).order_by(Tag.path)).scalars())
            persons = list(
                session.execute(select(Person).order_by(Person.name, Person.id)).scalars()
            )
            asset_tags = list(session.execute(select(AssetTag)).scalars())
            asset_people = list(session.execute(select(AssetPerson)).scalars())
            sources = list(session.execute(select(Source).order_by(Source.id)).scalars())
            job_run = session.execute(
                select(JobRun).order_by(JobRun.id.desc())
            ).scalar_one()

        assets_by_external_id = {asset.external_id: asset for asset in assets}

        assert result.status == "completed"
        assert result.processed_catalog_count == 1
        assert result.processed_asset_count == 3
        assert result.persisted_asset_count == 3
        assert result.error_count == 0

        assert len(assets) == 3
        assert len(tags) == 10
        assert len(persons) == 3
        assert len(asset_tags) == 17
        assert len(asset_people) == 5

        assert [asset.external_id for asset in assets] == [
            "0B2B664356B0F811D277461F8953ABE4",
            _FIRST_ASSET_EXTERNAL_ID,
            _SECOND_ASSET_EXTERNAL_ID,
        ]
        assert assets_by_external_id[_SECOND_ASSET_EXTERNAL_ID].summary == "Title 2"
        assert assets_by_external_id[_SECOND_ASSET_EXTERNAL_ID].metadata_json == {
            "file_name": "monalisa-2.jpg",
            "file_path": (
                "C:/Users/phili/Desktop/Source/pixelpast-core/test/assets/"
                "monalisa-2.jpg"
            ),
            "preserved_file_name": "monalisa-2.jpg",
            "caption": None,
            "camera": None,
            "lens": None,
            "aperture_f_number": None,
            "shutter_speed_seconds": None,
            "iso": None,
            "rating": 4,
            "color_label": "Gelb",
            "collections": [],
            "face_regions": [
                {
                    "name": "Mona Lisa",
                    "left": 0.10048499999999999,
                    "top": 0.09559,
                    "right": 0.348035,
                    "bottom": 0.33701,
                },
                {
                    "name": "John Doe",
                    "left": 0.486525,
                    "top": 0.460785,
                    "right": 0.814955,
                    "bottom": 0.8063750000000001,
                },
            ],
        }
        assert [tag.path for tag in tags] == [
            "events",
            "events|vacation",
            "events|vacation|Italy",
            "events|vacation|Italy|San Marino",
            "events|vacation|München",
            "events|wedding",
            "who",
            "who|Persons",
            "who|Persons|John Doe",
            "who|Persons|Mona Lisa",
        ]
        assert [person.name for person in persons] == [
            "John Doe",
            "Leonardo da Vinci",
            "Mona Lisa",
        ]
        assert len(sources) == 1
        assert sources[0].type == "lightroom_catalog"
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


def test_lightroom_catalog_ingestion_is_idempotent_and_reuses_asset_by_document_id() -> (
    None
):
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    try:
        catalog_path = _copy_fixture_catalog(workspace_root)

        first_result = LightroomCatalogIngestionService().ingest(
            runtime=runtime,
            root=catalog_path,
        )
        with runtime.session_factory() as session:
            first_assets = {
                asset.external_id: asset.id
                for asset in session.execute(select(Asset)).scalars()
            }

        _rename_lightroom_file_base_name(
            catalog_path=catalog_path,
            root_file_id=118,
            new_base_name="renamed-monalisa-2",
        )
        second_result = LightroomCatalogIngestionService().ingest(
            runtime=runtime,
            root=catalog_path,
        )

        with runtime.session_factory() as session:
            second_assets = {
                asset.external_id: asset
                for asset in session.execute(select(Asset)).scalars()
            }
            latest_job_run = session.execute(
                select(JobRun).order_by(JobRun.id.desc())
            ).scalars().first()

        assert first_result.status == "completed"
        assert second_result.status == "completed"
        assert len(second_assets) == 3
        assert latest_job_run is not None
        assert second_assets[_SECOND_ASSET_EXTERNAL_ID].id == first_assets[
            _SECOND_ASSET_EXTERNAL_ID
        ]
        assert second_assets[_SECOND_ASSET_EXTERNAL_ID].metadata_json is not None
        assert second_assets[_SECOND_ASSET_EXTERNAL_ID].metadata_json["file_name"] == (
            "renamed-monalisa-2.jpg"
        )
        assert second_assets[_SECOND_ASSET_EXTERNAL_ID].metadata_json["file_path"].endswith(
            "/renamed-monalisa-2.jpg"
        )
        assert (
            second_assets[_SECOND_ASSET_EXTERNAL_ID].metadata_json[
                "preserved_file_name"
            ]
            == "monalisa-2.jpg"
        )
        assert latest_job_run.progress_json == {
            "total": 1,
            "completed": 1,
            "inserted": 0,
            "updated": 1,
            "unchanged": 2,
            "skipped": 0,
            "failed": 0,
            "missing_from_source": 0,
            "persisted_asset_count": 3,
        }
    finally:
        runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_lightroom_catalog_ingestion_persists_caption_and_collection_metadata_and_ignores_virtual_copies() -> (
    None
):
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    try:
        catalog_path = _copy_fixture_catalog(workspace_root)
        _set_lightroom_caption(
            catalog_path=catalog_path,
            image_id=67,
            caption="A painted portrait.",
        )
        _insert_static_collection_membership(
            catalog_path=catalog_path,
            image_id=67,
            root_collection_id=900,
            child_collection_id=901,
        )
        _insert_virtual_copy_row(
            catalog_path=catalog_path,
            image_id=999,
            root_file_id=71,
        )

        result = LightroomCatalogIngestionService().ingest(
            runtime=runtime,
            root=catalog_path,
        )

        with runtime.session_factory() as session:
            assets = {
                asset.external_id: asset
                for asset in session.execute(select(Asset)).scalars()
            }

        assert result.status == "completed"
        assert result.processed_asset_count == 3
        assert result.persisted_asset_count == 3
        assert len(assets) == 3
        assert assets[_FIRST_ASSET_EXTERNAL_ID].metadata_json is not None
        assert assets[_FIRST_ASSET_EXTERNAL_ID].metadata_json["caption"] == (
            "A painted portrait."
        )
        assert assets[_FIRST_ASSET_EXTERNAL_ID].metadata_json["collections"] == [
            {
                "id": 901,
                "name": "Italy",
                "path": "Trips/Italy",
            }
        ]
        assert assets[_FIRST_ASSET_EXTERNAL_ID].metadata_json["face_regions"] == [
            {
                "name": "Mona Lisa",
                "left": 0.29167,
                "top": 0.25980499999999995,
                "right": 0.58579,
                "bottom": 0.537995,
            }
        ]
    finally:
        runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_lightroom_catalog_ingestion_reads_runtime_catalog_path_and_emits_progress() -> (
    None
):
    workspace_root = _create_workspace_root()
    runtime = None
    try:
        catalog_path = _copy_fixture_catalog(workspace_root)
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


def test_lightroom_catalog_ingestion_can_limit_import_to_deterministic_asset_range() -> (
    None
):
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    try:
        catalog_path = _copy_fixture_catalog(workspace_root)

        result = LightroomCatalogIngestionService().ingest(
            runtime=runtime,
            root=catalog_path,
            start_index=2,
            end_index=3,
        )

        with runtime.session_factory() as session:
            assets = list(
                session.execute(select(Asset).order_by(Asset.external_id)).scalars()
            )
            latest_job_run = session.execute(
                select(JobRun).order_by(JobRun.id.desc())
            ).scalars().first()

        assert result.status == "completed"
        assert result.processed_catalog_count == 1
        assert result.processed_asset_count == 2
        assert result.persisted_asset_count == 2
        assert [asset.external_id for asset in assets] == [
            "0B2B664356B0F811D277461F8953ABE4",
            _SECOND_ASSET_EXTERNAL_ID,
        ]
        assert latest_job_run is not None
        assert latest_job_run.progress_json == {
            "total": 1,
            "completed": 1,
            "inserted": 2,
            "updated": 0,
            "unchanged": 0,
            "skipped": 0,
            "failed": 0,
            "missing_from_source": 0,
            "persisted_asset_count": 2,
        }
    finally:
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


def test_lightroom_catalog_ingestion_rejects_invalid_asset_range() -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    try:
        catalog_path = _copy_fixture_catalog(workspace_root)

        with pytest.raises(
            ValueError,
            match="start index must be less than or equal to the end index",
        ):
            LightroomCatalogIngestionService().ingest(
                runtime=runtime,
                root=catalog_path,
                start_index=3,
                end_index=2,
            )
    finally:
        runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_lightroom_catalog_ingestion_rejects_unsupported_configured_file_type() -> None:
    workspace_root = _create_workspace_root()
    runtime = None
    try:
        unsupported_path = workspace_root / "fixture-copy.txt"
        unsupported_path.write_text("not a lightroom catalog", encoding="utf-8")
        runtime = _create_runtime(lightroom_catalog_path=unsupported_path)

        with pytest.raises(ValueError, match="supported extensions"):
            LightroomCatalogIngestionService().ingest(runtime=runtime)

        with runtime.session_factory() as session:
            job_run = session.execute(
                select(JobRun).order_by(JobRun.id.desc())
            ).scalar_one()

        assert job_run.status == "failed"
        assert job_run.phase == "filesystem discovery"
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_lightroom_catalog_ingestion_rejects_invalid_sqlite_catalog() -> None:
    workspace_root = _create_workspace_root()
    runtime = None
    try:
        invalid_catalog_path = workspace_root / "broken-catalog.lrcat"
        invalid_catalog_path.write_bytes(b"this is not a sqlite database")
        runtime = _create_runtime(lightroom_catalog_path=invalid_catalog_path)

        with pytest.raises(sqlite3.DatabaseError, match="file is not a database"):
            LightroomCatalogIngestionService().ingest(runtime=runtime)

        with runtime.session_factory() as session:
            job_run = session.execute(
                select(JobRun).order_by(JobRun.id.desc())
            ).scalar_one()
            assets = list(session.execute(select(Asset)).scalars())

        assert job_run.status == "failed"
        assert job_run.phase == "metadata extraction"
        assert assets == []
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_lightroom_catalog_ingestion_treats_malformed_xmp_blob_as_partial_failure() -> (
    None
):
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    try:
        catalog_path = _copy_fixture_catalog(workspace_root)
        _corrupt_xmp_blob(catalog_path=catalog_path, image_id=68)

        result = LightroomCatalogIngestionService().ingest(
            runtime=runtime,
            root=catalog_path,
        )

        with runtime.session_factory() as session:
            assets = list(session.execute(select(Asset)).scalars())
            job_run = session.execute(
                select(JobRun).order_by(JobRun.id.desc())
            ).scalar_one()

        assert result.status == "partial_failure"
        assert result.processed_catalog_count == 0
        assert result.processed_asset_count == 0
        assert result.persisted_asset_count == 0
        assert result.error_count == 1
        assert "decompress" in result.transform_errors[0].message
        assert assets == []
        assert job_run.status == "partial_failure"
        assert job_run.progress_json == {
            "total": 1,
            "completed": 1,
            "inserted": 0,
            "updated": 0,
            "unchanged": 0,
            "skipped": 0,
            "failed": 1,
            "missing_from_source": 0,
            "persisted_asset_count": 0,
        }
    finally:
        runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


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


def _copy_fixture_catalog(workspace_root: Path) -> Path:
    catalog_path = workspace_root / _FIXTURE_PATH.name
    shutil.copy2(_FIXTURE_PATH, catalog_path)
    return catalog_path


def _set_lightroom_caption(
    *,
    catalog_path: Path,
    image_id: int,
    caption: str,
) -> None:
    with sqlite3.connect(catalog_path) as connection:
        connection.execute(
            "UPDATE AgLibraryIPTC SET caption = ? WHERE image = ?",
            (caption, image_id),
        )
        connection.commit()


def _rename_lightroom_file_base_name(
    *,
    catalog_path: Path,
    root_file_id: int,
    new_base_name: str,
) -> None:
    with sqlite3.connect(catalog_path) as connection:
        connection.execute(
            "UPDATE AgLibraryFile SET baseName = ? WHERE id_local = ?",
            (new_base_name, root_file_id),
        )
        connection.commit()


def _insert_static_collection_membership(
    *,
    catalog_path: Path,
    image_id: int,
    root_collection_id: int,
    child_collection_id: int,
) -> None:
    with sqlite3.connect(catalog_path) as connection:
        connection.execute(
            """
            INSERT INTO AgLibraryCollection (
                id_local,
                creationId,
                genealogy,
                imageCount,
                name,
                parent,
                systemOnly
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (root_collection_id, "", "", None, "Trips", None, ""),
        )
        connection.execute(
            """
            INSERT INTO AgLibraryCollection (
                id_local,
                creationId,
                genealogy,
                imageCount,
                name,
                parent,
                systemOnly
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (child_collection_id, "", "", None, "Italy", root_collection_id, ""),
        )
        connection.execute(
            """
            INSERT INTO AgLibraryCollectionImage (
                id_local,
                collection,
                image,
                pick,
                positionInCollection
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (child_collection_id, child_collection_id, image_id, 0, None),
        )
        connection.commit()


def _insert_virtual_copy_row(
    *,
    catalog_path: Path,
    image_id: int,
    root_file_id: int,
) -> None:
    with sqlite3.connect(catalog_path) as connection:
        connection.execute(
            """
            INSERT INTO Adobe_images (
                id_local,
                id_global,
                captureTime,
                colorLabels,
                copyName,
                copyReason,
                fileFormat,
                pick,
                positionInFolder,
                rating,
                rootFile,
                touchCount,
                touchTime
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                image_id,
                f"virtual-copy-{image_id}",
                "2020-01-01T02:03:40.000",
                "Rot",
                "Virtual Copy 1",
                "copy",
                "JPEG",
                0,
                "zz",
                1,
                root_file_id,
                0,
                0,
            ),
        )
        connection.commit()


def _corrupt_xmp_blob(*, catalog_path: Path, image_id: int) -> None:
    with sqlite3.connect(catalog_path) as connection:
        original_blob = connection.execute(
            "SELECT xmp FROM Adobe_AdditionalMetadata WHERE image = ?",
            (image_id,),
        ).fetchone()[0]
        connection.execute(
            "UPDATE Adobe_AdditionalMetadata SET xmp = ? WHERE image = ?",
            (original_blob[:4] + b"not-a-valid-zlib-stream", image_id),
        )
        connection.commit()
