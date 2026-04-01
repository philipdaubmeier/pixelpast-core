"""Tests for album-navigation schema, repositories, and fill-in behavior."""

from __future__ import annotations

from sqlalchemy import select

from pixelpast.persistence.models import Asset, AssetCollection, AssetCollectionItem, Source
from pixelpast.persistence.repositories import (
    AlbumNavigationRepository,
    AssetFolderRepository,
    AssetRepository,
)
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import Settings


def test_album_navigation_fill_in_builds_photo_folder_tree_from_existing_assets() -> None:
    runtime = _create_runtime()
    try:
        with runtime.session_factory() as session:
            source = Source(
                name="Photos",
                type="photos",
                config={"root_path": "/library/photos"},
            )
            session.add(source)
            session.flush()
            session.add_all(
                [
                    Asset(
                        source_id=source.id,
                        external_id="/library/photos/2024/Trip/image-1.jpg",
                        media_type="photo",
                        timestamp=_timestamp(),
                        metadata_json={
                            "source_path": "/library/photos/2024/Trip/image-1.jpg"
                        },
                    ),
                    Asset(
                        source_id=source.id,
                        external_id="/library/photos/root-image.jpg",
                        media_type="photo",
                        timestamp=_timestamp(),
                        metadata_json={"source_path": "/library/photos/root-image.jpg"},
                    ),
                    Asset(
                        source_id=source.id,
                        external_id="legacy-photo-without-path",
                        media_type="photo",
                        timestamp=_timestamp(),
                        metadata_json={},
                    ),
                ]
            )
            session.commit()

        with runtime.session_factory() as session:
            result = AlbumNavigationRepository(session).fill_from_existing_assets(
                source_id=1
            )
            session.commit()

            assets = list(session.execute(select(Asset).order_by(Asset.id)).scalars())
            folders = AssetFolderRepository(session).list_by_source_id(source_id=1)

        assert result.created_folder_count == 3
        assert result.assigned_asset_folder_count == 2
        assert result.unresolved_asset_count == 1
        assert [folder.path for folder in folders] == [
            "photos",
            "photos/2024",
            "photos/2024/Trip",
        ]
        assert assets[0].folder_id == folders[-1].id
        assert assets[1].folder_id == folders[0].id
        assert assets[2].folder_id is None
    finally:
        runtime.engine.dispose()


def test_album_navigation_fill_in_builds_lightroom_collections_and_memberships() -> None:
    runtime = _create_runtime()
    try:
        with runtime.session_factory() as session:
            source = Source(
                name="Lightroom",
                type="lightroom_catalog",
                external_id="catalog:test",
                config={"catalog_path": "C:/catalogs/test.lrcat"},
            )
            session.add(source)
            session.flush()
            session.add_all(
                [
                    Asset(
                        source_id=source.id,
                        external_id="doc-1",
                        media_type="photo",
                        timestamp=_timestamp(),
                        metadata_json={
                            "file_path": "C:/photos/Trips/root.jpg",
                            "collections": [
                                {"id": 900, "name": "Trips", "path": "Trips"}
                            ],
                        },
                    ),
                    Asset(
                        source_id=source.id,
                        external_id="doc-2",
                        media_type="photo",
                        timestamp=_timestamp(),
                        metadata_json={
                            "file_path": "C:/photos/Trips/Italy/leaf.jpg",
                            "collections": [
                                {"id": 901, "name": "Italy", "path": "Trips/Italy"}
                            ],
                        },
                    ),
                ]
            )
            session.commit()

        with runtime.session_factory() as session:
            result = AlbumNavigationRepository(session).fill_from_existing_assets()
            session.commit()

            collections = list(
                session.execute(
                    select(AssetCollection).order_by(AssetCollection.path, AssetCollection.id)
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
            assets = list(session.execute(select(Asset).order_by(Asset.id)).scalars())

        collection_by_path = {collection.path: collection for collection in collections}
        assert result.created_collection_count == 2
        assert result.linked_collection_item_count == 2
        assert collection_by_path["Trips"].parent_id is None
        assert (
            collection_by_path["Trips/Italy"].parent_id
            == collection_by_path["Trips"].id
        )
        assert len(collection_items) == 2
        assert assets[0].folder_id is not None
        assert assets[1].folder_id is not None
        assert collection_by_path["Trips"].metadata_json == {
            "fill_in_source": "asset.metadata.collections"
        }
    finally:
        runtime.engine.dispose()


def test_asset_repository_upsert_persists_folder_id() -> None:
    runtime = _create_runtime()
    try:
        with runtime.session_factory() as session:
            source = Source(name="Photos", type="photos", config={"root_path": "/library/photos"})
            session.add(source)
            session.flush()
            folder, _ = AssetFolderRepository(session).get_or_create_tree(
                source_id=source.id,
                path="photos/2024",
            )

            repository = AssetRepository(session)
            inserted = repository.upsert(
                source_id=source.id,
                external_id="/library/photos/2024/image.jpg",
                media_type="photo",
                timestamp=_timestamp(),
                summary=None,
                latitude=None,
                longitude=None,
                folder_id=folder.id,
                creator_person_id=None,
                metadata_json={"source_path": "/library/photos/2024/image.jpg"},
            )
            updated = repository.upsert(
                source_id=source.id,
                external_id="/library/photos/2024/image.jpg",
                media_type="photo",
                timestamp=_timestamp(),
                summary=None,
                latitude=None,
                longitude=None,
                folder_id=None,
                creator_person_id=None,
                metadata_json={"source_path": "/library/photos/2024/image.jpg"},
            )
            session.commit()

            persisted = session.execute(select(Asset)).scalar_one()

        assert inserted.status == "inserted"
        assert updated.status == "updated"
        assert persisted.folder_id is None
    finally:
        runtime.engine.dispose()


def _create_runtime():
    runtime = create_runtime_context(settings=Settings(database_url="sqlite://"))
    initialize_database(runtime)
    return runtime


def _timestamp():
    from datetime import UTC, datetime

    return datetime(2024, 1, 2, 3, 4, 5, tzinfo=UTC)
