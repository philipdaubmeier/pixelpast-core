"""Integration tests for Lightroom catalog persistence and lifecycle seams."""

from __future__ import annotations

import shutil
import sqlite3
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from pixelpast.ingestion.lightroom_catalog import (
    LightroomCatalogConnector,
    LightroomCatalogDescriptor,
    LightroomCatalogIngestionPersistenceScope,
    LightroomCatalogIngestionRunCoordinator,
    LightroomCatalogTransformer,
    build_lightroom_catalog_source_external_id,
)
from pixelpast.persistence.models import (
    Asset,
    AssetCollection,
    AssetCollectionItem,
    AssetFolder,
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


def test_lightroom_catalog_persistence_scope_persists_assets_and_is_idempotent() -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    try:
        catalog_path = workspace_root / _FIXTURE_PATH.name
        shutil.copy2(_FIXTURE_PATH, catalog_path)
        descriptor = LightroomCatalogDescriptor(path=catalog_path)

        first_candidate = _build_catalog_candidate(descriptor=descriptor)
        lifecycle = LightroomCatalogIngestionRunCoordinator()
        first_run_id = lifecycle.create_run(
            runtime=runtime,
            resolved_root=catalog_path.resolve(),
        )
        first_scope = LightroomCatalogIngestionPersistenceScope(
            runtime=runtime,
            lifecycle=lifecycle,
            resolved_root=catalog_path.resolve(),
        )
        first_missing = first_scope.count_missing_from_source(
            resolved_root=catalog_path.resolve(),
            discovered_units=(descriptor,),
            candidates=(first_candidate,),
        )
        first_outcome = first_scope.persist(candidate=first_candidate)
        first_scope.commit()
        first_scope.close()

        second_candidate = _build_catalog_candidate(descriptor=descriptor)
        second_run_id = lifecycle.create_run(
            runtime=runtime,
            resolved_root=catalog_path.resolve(),
        )
        second_scope = LightroomCatalogIngestionPersistenceScope(
            runtime=runtime,
            lifecycle=lifecycle,
            resolved_root=catalog_path.resolve(),
        )
        second_outcome = second_scope.persist(candidate=second_candidate)
        second_scope.commit()
        second_scope.close()

        renamed_asset = replace(
            second_candidate.assets[1],
            folder_path="C:/renamed",
            metadata_json={
                **(second_candidate.assets[1].metadata_json or {}),
                "file_name": "renamed-monalisa-2.jpg",
                "file_path": "C:/renamed/renamed-monalisa-2.jpg",
            },
        )
        renamed_candidate = replace(
            second_candidate,
            assets=(
                second_candidate.assets[0],
                renamed_asset,
                second_candidate.assets[2],
            ),
        )
        third_run_id = lifecycle.create_run(
            runtime=runtime,
            resolved_root=catalog_path.resolve(),
        )
        third_scope = LightroomCatalogIngestionPersistenceScope(
            runtime=runtime,
            lifecycle=lifecycle,
            resolved_root=catalog_path.resolve(),
        )
        third_outcome = third_scope.persist(candidate=renamed_candidate)
        third_scope.commit()
        third_scope.close()

        with runtime.session_factory() as session:
            assets = list(session.execute(select(Asset).order_by(Asset.external_id)).scalars())
            folders = list(
                session.execute(select(AssetFolder).order_by(AssetFolder.path)).scalars()
            )
            collections = list(
                session.execute(
                    select(AssetCollection).order_by(
                        AssetCollection.path,
                        AssetCollection.id,
                    )
                ).scalars()
            )
            collection_items = list(
                session.execute(
                    select(AssetCollectionItem).order_by(
                        AssetCollectionItem.collection_id,
                        AssetCollectionItem.asset_id,
                    )
                ).scalars()
            )
            people = list(session.execute(select(Person).order_by(Person.name)).scalars())
            tags = list(session.execute(select(Tag).order_by(Tag.path)).scalars())
            asset_tags = list(session.execute(select(AssetTag)).scalars())
            asset_people = list(session.execute(select(AssetPerson)).scalars())
            sources = list(session.execute(select(Source).order_by(Source.id)).scalars())
            job_runs = list(session.execute(select(JobRun).order_by(JobRun.id)).scalars())

        asset_by_external_id = {asset.external_id: asset for asset in assets}
        renamed_external_id = second_candidate.assets[1].external_id

        assert first_run_id == 1
        assert second_run_id == 2
        assert third_run_id == 3
        assert first_missing == 0
        assert first_outcome == (
            "inserted=3;updated=0;unchanged=0;missing_from_source=0;"
            "skipped=0;persisted_asset_count=3"
        )
        assert second_outcome == (
            "inserted=0;updated=0;unchanged=3;missing_from_source=0;"
            "skipped=0;persisted_asset_count=3"
        )
        assert third_outcome == (
            "inserted=0;updated=1;unchanged=2;missing_from_source=0;"
            "skipped=0;persisted_asset_count=3"
        )

        assert len(assets) == 3
        folder_by_path = {folder.path: folder for folder in folders}
        assert [folder.path for folder in folders] == _expected_folder_paths(
            "C:/Users/phili/Desktop/Source/pixelpast-core/test/assets",
            "C:/renamed",
        )
        assert asset_by_external_id[_FIRST_ASSET_EXTERNAL_ID].folder_id == folder_by_path[
            "C:/Users/phili/Desktop/Source/pixelpast-core/test/assets"
        ].id
        assert asset_by_external_id["0B2B664356B0F811D277461F8953ABE4"].folder_id == (
            folder_by_path["C:/Users/phili/Desktop/Source/pixelpast-core/test/assets"].id
        )
        assert asset_by_external_id[renamed_external_id].folder_id == folder_by_path[
            "C:/renamed"
        ].id
        assert collections == []
        assert collection_items == []
        assert len(people) == 3
        assert len(tags) == 6
        assert len(asset_tags) == 11
        assert len(asset_people) == 5
        assert len(sources) == 1
        assert len(job_runs) == 3

        assert sources[0].type == "lightroom_catalog"
        assert sources[0].external_id == build_lightroom_catalog_source_external_id(
            catalog_path=catalog_path.resolve()
        )
        assert sources[0].config == {"catalog_path": catalog_path.resolve().as_posix()}
        assert [job_run.job for job_run in job_runs] == ["lightroom_catalog"] * 3

        renamed_asset_model = asset_by_external_id[renamed_external_id]
        assert renamed_asset_model.summary == "Title 2"
        assert renamed_asset_model.metadata_json == {
            "file_name": "renamed-monalisa-2.jpg",
            "file_path": "C:/renamed/renamed-monalisa-2.jpg",
            "preserved_file_name": "monalisa-2.jpg",
            "caption": None,
            "camera": None,
            "lens": None,
            "aperture_f_number": None,
            "shutter_speed_seconds": None,
            "iso": None,
            "rating": 4,
            "color_label": "Gelb",
            "explicit_keywords": [
                "Italy",
                "John Doe",
                "Mona Lisa",
                "San Marino",
                "events",
                "vacation",
            ],
            "hierarchical_subjects": [
                "events|vacation",
                "events|vacation|Italy|San Marino",
                "who|Persons|John Doe",
                "who|Persons|Mona Lisa",
            ],
            "linked_tag_paths": [
                "events|vacation|Italy",
                "events|vacation|Italy|San Marino",
                "events",
                "events|vacation",
            ],
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
        assert {person.name for person in people} == {
            "John Doe",
            "Leonardo da Vinci",
            "Mona Lisa",
        }
    finally:
        runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_lightroom_catalog_run_coordinator_persists_source_and_initial_job_run() -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    try:
        catalog_path = workspace_root / _FIXTURE_PATH.name
        shutil.copy2(_FIXTURE_PATH, catalog_path)

        run_id = LightroomCatalogIngestionRunCoordinator().create_run(
            runtime=runtime,
            resolved_root=catalog_path.resolve(),
        )

        with runtime.session_factory() as session:
            source = session.execute(select(Source)).scalar_one()
            job_run = session.execute(
                select(JobRun).where(JobRun.id == run_id)
            ).scalar_one()

        assert source.type == "lightroom_catalog"
        assert source.external_id == build_lightroom_catalog_source_external_id(
            catalog_path=catalog_path.resolve()
        )
        assert source.config == {"catalog_path": catalog_path.resolve().as_posix()}
        assert job_run.type == "ingest"
        assert job_run.job == "lightroom_catalog"
        assert job_run.mode == "full"
        assert job_run.phase == "initializing"
        assert job_run.status == "running"
        assert job_run.progress_json == {
            "total": None,
            "completed": 0,
            "inserted": 0,
            "updated": 0,
            "unchanged": 0,
            "skipped": 0,
            "failed": 0,
            "missing_from_source": 0,
            "root_path": catalog_path.resolve().as_posix(),
        }
    finally:
        runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_lightroom_catalog_persistence_scope_persists_collection_tree_and_reconciles_memberships(
) -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    try:
        catalog_path = workspace_root / _FIXTURE_PATH.name
        shutil.copy2(_FIXTURE_PATH, catalog_path)
        _insert_static_collection_membership(
            catalog_path=catalog_path,
            image_id=67,
            root_collection_id=900,
            child_collection_id=901,
        )
        _insert_static_collection_membership(
            catalog_path=catalog_path,
            image_id=68,
            root_collection_id=900,
            child_collection_id=902,
            child_collection_name="Favorites",
        )
        descriptor = LightroomCatalogDescriptor(path=catalog_path)
        lifecycle = LightroomCatalogIngestionRunCoordinator()

        first_candidate = _build_catalog_candidate(descriptor=descriptor)
        lifecycle.create_run(runtime=runtime, resolved_root=catalog_path.resolve())
        first_scope = LightroomCatalogIngestionPersistenceScope(
            runtime=runtime,
            lifecycle=lifecycle,
            resolved_root=catalog_path.resolve(),
        )
        first_scope.persist(candidate=first_candidate)
        first_scope.commit()
        first_scope.close()

        _delete_collection_membership(catalog_path=catalog_path, image_id=67)
        second_candidate = _build_catalog_candidate(descriptor=descriptor)
        lifecycle.create_run(runtime=runtime, resolved_root=catalog_path.resolve())
        second_scope = LightroomCatalogIngestionPersistenceScope(
            runtime=runtime,
            lifecycle=lifecycle,
            resolved_root=catalog_path.resolve(),
        )
        second_scope.persist(candidate=second_candidate)
        second_scope.commit()
        second_scope.close()

        with runtime.session_factory() as session:
            assets = {
                asset.external_id: asset
                for asset in session.execute(select(Asset)).scalars()
            }
            folders = list(
                session.execute(select(AssetFolder).order_by(AssetFolder.path)).scalars()
            )
            collections = list(
                session.execute(
                    select(AssetCollection).order_by(
                        AssetCollection.path,
                        AssetCollection.id,
                    )
                ).scalars()
            )
            collection_items = list(
                session.execute(
                    select(AssetCollectionItem).order_by(
                        AssetCollectionItem.collection_id,
                        AssetCollectionItem.asset_id,
                    )
                ).scalars()
                )

        folder_by_path = {folder.path: folder for folder in folders}
        collection_by_path = {collection.path: collection for collection in collections}
        assert [folder.path for folder in folders] == _expected_folder_paths(
            "C:/Users/phili/Desktop/Source/pixelpast-core/test/assets"
        )
        assert assets[_FIRST_ASSET_EXTERNAL_ID].folder_id == folder_by_path[
            "C:/Users/phili/Desktop/Source/pixelpast-core/test/assets"
        ].id
        assert assets[_SECOND_ASSET_EXTERNAL_ID].folder_id == folder_by_path[
            "C:/Users/phili/Desktop/Source/pixelpast-core/test/assets"
        ].id
        assert [collection.path for collection in collections] == [
            "Trips",
            "Trips/Favorites",
            "Trips/Italy",
        ]
        assert collection_by_path["Trips"].parent_id is None
        assert (
            collection_by_path["Trips/Italy"].parent_id
            == collection_by_path["Trips"].id
        )
        assert (
            collection_by_path["Trips/Favorites"].parent_id
            == collection_by_path["Trips"].id
        )
        assert [item.asset_id for item in collection_items] == [
            assets[_SECOND_ASSET_EXTERNAL_ID].id
        ]
    finally:
        runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def _build_catalog_candidate(*, descriptor: LightroomCatalogDescriptor):
    connector = LightroomCatalogConnector()
    loaded_catalog = connector.fetch_catalogs(catalogs=(descriptor,))[0]
    return LightroomCatalogTransformer().build_catalog_candidate(loaded_catalog)


def _create_runtime():
    runtime = create_runtime_context(settings=Settings(database_url="sqlite://"))
    initialize_database(runtime)
    return runtime


def _create_workspace_root() -> Path:
    workspace_root = Path("var") / f"lightroom-catalog-{uuid4().hex}"
    workspace_root.mkdir(parents=True, exist_ok=False)
    return workspace_root


def _expected_folder_paths(*leaf_paths: str) -> list[str]:
    ordered_paths: list[str] = []
    seen: set[str] = set()
    for leaf_path in leaf_paths:
        parts = [part for part in leaf_path.split("/") if part]
        for index in range(1, len(parts) + 1):
            candidate = "/".join(parts[:index])
            if candidate in seen:
                continue
            seen.add(candidate)
            ordered_paths.append(candidate)
    return sorted(ordered_paths)


def _insert_static_collection_membership(
    *,
    catalog_path: Path,
    image_id: int,
    root_collection_id: int,
    child_collection_id: int,
    child_collection_name: str = "Italy",
) -> None:
    with sqlite3.connect(catalog_path) as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO AgLibraryCollection (
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
            INSERT OR REPLACE INTO AgLibraryCollection (
                id_local,
                creationId,
                genealogy,
                imageCount,
                name,
                parent,
                systemOnly
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (child_collection_id, "", "", None, child_collection_name, root_collection_id, ""),
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


def _delete_collection_membership(*, catalog_path: Path, image_id: int) -> None:
    with sqlite3.connect(catalog_path) as connection:
        connection.execute(
            "DELETE FROM AgLibraryCollectionImage WHERE image = ?",
            (image_id,),
        )
        connection.commit()
