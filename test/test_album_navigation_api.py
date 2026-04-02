"""Integration tests for album-navigation API contracts."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from pixelpast.api.app import create_app
from pixelpast.persistence.models import (
    Asset,
    AssetCollection,
    AssetCollectionItem,
    AssetFolder,
    AssetPerson,
    AssetTag,
    Person,
    Source,
    Tag,
)
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import Settings


def test_album_folder_tree_lists_stable_nodes_with_filtered_counts() -> None:
    workspace_root = _create_workspace_dir(prefix="album-folder-tree")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        _seed_album_navigation_data(runtime)

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get(
                "/api/albums/folders",
                params=[("person_ids", 1), ("tag_paths", "travel/italy")],
            )

        assert response.status_code == 200
        assert response.json() == {
            "supported_filters": ["person_ids", "tag_paths", "filename_query"],
            "applied_filters": {
                "person_ids": [1],
                "tag_paths": ["travel/italy"],
                "filename_query": None,
            },
            "nodes": [
                {
                    "id": 1,
                    "source_id": 1,
                    "source_name": "Photos",
                    "source_type": "photos",
                    "parent_id": None,
                    "name": "photos",
                    "path": "photos",
                    "child_count": 1,
                    "asset_count": 1,
                },
                {
                    "id": 2,
                    "source_id": 1,
                    "source_name": "Photos",
                    "source_type": "photos",
                    "parent_id": 1,
                    "name": "2024",
                    "path": "photos/2024",
                    "child_count": 2,
                    "asset_count": 1,
                },
                {
                    "id": 4,
                    "source_id": 1,
                    "source_name": "Photos",
                    "source_type": "photos",
                    "parent_id": 2,
                    "name": "Home",
                    "path": "photos/2024/Home",
                    "child_count": 0,
                    "asset_count": 0,
                },
                {
                    "id": 3,
                    "source_id": 1,
                    "source_name": "Photos",
                    "source_type": "photos",
                    "parent_id": 2,
                    "name": "Trip",
                    "path": "photos/2024/Trip",
                    "child_count": 0,
                    "asset_count": 1,
                },
            ],
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_album_collection_tree_lists_stable_nodes_with_deduplicated_counts() -> None:
    workspace_root = _create_workspace_dir(prefix="album-collection-tree")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        _seed_album_navigation_data(runtime)

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get("/api/albums/collections")

        assert response.status_code == 200
        assert response.json() == {
            "supported_filters": ["person_ids", "tag_paths", "filename_query"],
            "applied_filters": {
                "person_ids": [],
                "tag_paths": [],
                "filename_query": None,
            },
            "nodes": [
                {
                    "id": 1,
                    "source_id": 2,
                    "source_name": "Lightroom",
                    "source_type": "lightroom_catalog",
                    "parent_id": None,
                    "name": "Portraits",
                    "path": "Portraits",
                    "collection_type": "collection",
                    "child_count": 0,
                    "asset_count": 1,
                },
                {
                    "id": 2,
                    "source_id": 2,
                    "source_name": "Lightroom",
                    "source_type": "lightroom_catalog",
                    "parent_id": None,
                    "name": "Trips",
                    "path": "Trips",
                    "collection_type": "collection",
                    "child_count": 1,
                    "asset_count": 1,
                },
                {
                    "id": 3,
                    "source_id": 2,
                    "source_name": "Lightroom",
                    "source_type": "lightroom_catalog",
                    "parent_id": 2,
                    "name": "Italy",
                    "path": "Trips/Italy",
                    "collection_type": "collection",
                    "child_count": 0,
                    "asset_count": 1,
                },
            ],
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_album_folder_asset_listing_aggregates_descendants_in_stable_order() -> None:
    workspace_root = _create_workspace_dir(prefix="album-folder-listing")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        _seed_album_navigation_data(runtime)

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get("/api/albums/folders/2/assets")

        assert response.status_code == 200
        assert response.json() == {
            "supported_filters": ["person_ids", "tag_paths", "filename_query"],
            "applied_filters": {
                "person_ids": [],
                "tag_paths": [],
            },
            "selection": {
                "node_kind": "folder",
                "id": 2,
                "source_id": 1,
                "source_name": "Photos",
                "source_type": "photos",
                "parent_id": 1,
                "name": "2024",
                "path": "photos/2024",
                "asset_count": 3,
            },
            "items": [
                {
                    "id": 3,
                    "short_id": "PHOT0003",
                    "timestamp": "2024-07-07T08:00:00+00:00",
                    "media_type": "photo",
                    "title": "family-home.jpg",
                    "thumbnail_url": "/media/q200/PHOT0003.webp",
                },
                {
                    "id": 2,
                    "short_id": "PHOT0002",
                    "timestamp": "2024-07-06T12:00:00+00:00",
                    "media_type": "photo",
                    "title": "Evening Walk",
                    "thumbnail_url": "/media/q200/PHOT0002.webp",
                },
                {
                    "id": 1,
                    "short_id": "PHOT0001",
                    "timestamp": "2024-07-05T10:00:00+00:00",
                    "media_type": "photo",
                    "title": "venice-anna.jpg",
                    "thumbnail_url": "/media/q200/PHOT0001.webp",
                },
            ],
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_album_collection_asset_listing_supports_filters_and_empty_results() -> None:
    workspace_root = _create_workspace_dir(prefix="album-collection-listing")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        _seed_album_navigation_data(runtime)

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get(
                "/api/albums/collections/2/assets",
                params=[
                    ("person_ids", 1),
                    ("tag_paths", "travel/italy"),
                    ("filename_query", "italy"),
                ],
            )

        assert response.status_code == 200
        assert response.json() == {
            "supported_filters": ["person_ids", "tag_paths", "filename_query"],
            "applied_filters": {
                "person_ids": [1],
                "tag_paths": ["travel/italy"],
                "filename_query": "italy",
            },
            "selection": {
                "node_kind": "collection",
                "id": 2,
                "source_id": 2,
                "source_name": "Lightroom",
                "source_type": "lightroom_catalog",
                "name": "Trips",
                "path": "Trips",
                "asset_count": 1,
                "collection_type": "collection",
            },
            "items": [
                {
                    "id": 5,
                    "short_id": "LR000005",
                    "timestamp": "2024-08-02T11:00:00+00:00",
                    "media_type": "photo",
                    "title": "italy-lake.jpg",
                    "thumbnail_url": "/media/q200/LR000005.webp",
                }
            ],
        }

        with TestClient(app) as client:
            empty_response = client.get(
                "/api/albums/collections/2/assets",
                params=[("filename_query", "does-not-exist")],
            )

        assert empty_response.status_code == 200
        assert empty_response.json()["selection"]["asset_count"] == 0
        assert empty_response.json()["items"] == []
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_album_folder_context_returns_stable_people_tags_and_hover_links() -> None:
    workspace_root = _create_workspace_dir(prefix="album-folder-context")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        _seed_album_navigation_data(runtime)

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get("/api/albums/folders/2/context")

        assert response.status_code == 200
        assert response.json() == {
            "supported_filters": ["person_ids", "tag_paths", "filename_query"],
            "applied_filters": {
                "person_ids": [],
                "tag_paths": [],
            },
            "selection": {
                "node_kind": "folder",
                "id": 2,
                "source_id": 1,
                "source_name": "Photos",
                "source_type": "photos",
                "parent_id": 1,
                "name": "2024",
                "path": "photos/2024",
                "asset_count": 3,
            },
            "persons": [
                {
                    "id": 1,
                    "name": "Anna Becker",
                    "path": "family/anna",
                    "asset_count": 2,
                },
                {
                    "id": 2,
                    "name": "Milo Tan",
                    "path": "friends/milo",
                    "asset_count": 1,
                },
            ],
            "tags": [
                {"id": 3, "label": "Home", "path": "home", "asset_count": 1},
                {"id": 1, "label": "Travel", "path": "travel", "asset_count": 1},
                {"id": 2, "label": "Italy", "path": "travel/italy", "asset_count": 1},
            ],
            "map_points": [],
            "asset_contexts": [
                {
                    "asset_id": 3,
                    "person_ids": [1],
                    "tag_paths": ["home"],
                    "map_point_ids": [],
                },
                {
                    "asset_id": 2,
                    "person_ids": [2],
                    "tag_paths": ["travel"],
                    "map_point_ids": [],
                },
                {
                    "asset_id": 1,
                    "person_ids": [1],
                    "tag_paths": ["travel/italy"],
                    "map_point_ids": [],
                },
            ],
            "summary_counts": {
                "assets": 3,
                "people": 2,
                "tags": 3,
                "places": 0,
            },
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_album_collection_context_supports_filters_and_map_points() -> None:
    workspace_root = _create_workspace_dir(prefix="album-collection-context")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        _seed_album_navigation_data(runtime)

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get(
                "/api/albums/collections/2/context",
                params=[("person_ids", 1), ("tag_paths", "travel/italy")],
            )

        assert response.status_code == 200
        assert response.json() == {
            "supported_filters": ["person_ids", "tag_paths", "filename_query"],
            "applied_filters": {
                "person_ids": [1],
                "tag_paths": ["travel/italy"],
            },
            "selection": {
                "node_kind": "collection",
                "id": 2,
                "source_id": 2,
                "source_name": "Lightroom",
                "source_type": "lightroom_catalog",
                "name": "Trips",
                "path": "Trips",
                "asset_count": 1,
                "collection_type": "collection",
            },
            "persons": [
                {
                    "id": 1,
                    "name": "Anna Becker",
                    "path": "family/anna",
                    "asset_count": 1,
                }
            ],
            "tags": [
                {"id": 2, "label": "Italy", "path": "travel/italy", "asset_count": 1}
            ],
            "map_points": [
                {
                    "id": "asset:LR000005",
                    "latitude": 46.5833,
                    "longitude": 12.2,
                    "asset_count": 1,
                }
            ],
            "asset_contexts": [
                {
                    "asset_id": 5,
                    "person_ids": [1],
                    "tag_paths": ["travel/italy"],
                    "map_point_ids": ["asset:LR000005"],
                }
            ],
            "summary_counts": {
                "assets": 1,
                "people": 1,
                "tags": 1,
                "places": 1,
            },
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_album_routes_reject_unsupported_global_filters() -> None:
    workspace_root = _create_workspace_dir(prefix="album-unsupported-filters")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        _seed_album_navigation_data(runtime)

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get(
                "/api/albums/folders",
                params=[("location_geometry", "bbox:1,2,3,4"), ("distance_latitude", 52.5)],
            )

        assert response.status_code == 400
        assert response.json() == {
            "detail": (
                "unsupported album filters: distance_latitude, location_geometry; "
                "supported filters: person_ids, tag_paths, filename_query"
            )
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_album_asset_detail_returns_normalized_metadata_and_named_face_regions() -> None:
    workspace_root = _create_workspace_dir(prefix="album-asset-detail")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        _seed_album_navigation_data(runtime)

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get("/api/albums/assets/5")

        assert response.status_code == 200
        assert response.json() == {
            "id": 5,
            "short_id": "LR000005",
            "source_id": 2,
            "source_name": "Lightroom",
            "source_type": "lightroom_catalog",
            "media_type": "photo",
            "title": "italy-lake.jpg",
            "creator": "Anna Becker",
            "preserved_filename": "italy-lake-original.jpg",
            "caption": "Dolomites lakeside in morning light.",
            "description": "A quiet stop before the next trail.",
            "timestamp": "2024-08-02T11:00:00+00:00",
            "latitude": 46.5833,
            "longitude": 12.2,
            "camera": "Canon EOS R5",
            "lens": "RF24-70mm F2.8 L IS USM",
            "aperture_f_number": 2.8,
            "shutter_speed_seconds": 0.005,
            "focal_length_mm": 35.0,
            "iso": 400,
            "thumbnail_url": "/media/q200/LR000005.webp",
            "original_url": "/media/orig/LR000005",
            "tags": [
                {"id": 2, "label": "Italy", "path": "travel/italy"},
            ],
            "people": [
                {"id": 1, "name": "Anna Becker", "path": "family/anna"},
            ],
            "face_regions": [
                {
                    "name": "Anna Becker",
                    "left": 0.22,
                    "top": 0.14,
                    "right": 0.43,
                    "bottom": 0.51,
                }
            ],
        }
        assert "metadata" not in response.json()
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_album_asset_detail_handles_missing_optional_camera_metadata() -> None:
    workspace_root = _create_workspace_dir(prefix="album-asset-detail-empty-meta")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        _seed_album_navigation_data(runtime)

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get("/api/albums/assets/4")

        assert response.status_code == 200
        assert response.json() == {
            "id": 4,
            "short_id": "LR000004",
            "source_id": 2,
            "source_name": "Lightroom",
            "source_type": "lightroom_catalog",
            "media_type": "photo",
            "title": "portrait-anna.jpg",
            "creator": None,
            "preserved_filename": None,
            "caption": None,
            "description": None,
            "timestamp": "2024-08-01T09:00:00+00:00",
            "latitude": None,
            "longitude": None,
            "camera": None,
            "lens": None,
            "aperture_f_number": None,
            "shutter_speed_seconds": None,
            "focal_length_mm": None,
            "iso": None,
            "thumbnail_url": "/media/q200/LR000004.webp",
            "original_url": "/media/orig/LR000004",
            "tags": [
                {"id": 3, "label": "Home", "path": "home"},
            ],
            "people": [
                {"id": 1, "name": "Anna Becker", "path": "family/anna"},
            ],
            "face_regions": [],
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_album_asset_detail_returns_empty_face_regions_when_missing() -> None:
    workspace_root = _create_workspace_dir(prefix="album-asset-detail-no-faces")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        _seed_album_navigation_data(runtime)

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get("/api/albums/assets/2")

        assert response.status_code == 200
        assert response.json()["face_regions"] == []
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_album_asset_detail_returns_404_for_unknown_asset() -> None:
    workspace_root = _create_workspace_dir(prefix="album-asset-detail-missing")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        _seed_album_navigation_data(runtime)

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get("/api/albums/assets/999")

        assert response.status_code == 404
        assert response.json() == {"detail": "album asset 999 does not exist"}
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def _seed_album_navigation_data(runtime) -> None:
    with runtime.session_factory() as session:
        photos_source = Source(
            name="Photos",
            type="photos",
            external_id="photos:test",
            config={},
        )
        lightroom_source = Source(
            name="Lightroom",
            type="lightroom_catalog",
            external_id="lightroom:test",
            config={},
        )
        anna = Person(name="Anna Becker", aliases=[], path="family/anna", metadata_json=None)
        milo = Person(name="Milo Tan", aliases=[], path="friends/milo", metadata_json=None)
        travel_tag = Tag(label="Travel", path="travel", metadata_json=None)
        italy_tag = Tag(label="Italy", path="travel/italy", metadata_json=None)
        home_tag = Tag(label="Home", path="home", metadata_json=None)
        session.add_all(
            [photos_source, lightroom_source, anna, milo, travel_tag, italy_tag, home_tag]
        )
        session.flush()

        folder_root = AssetFolder(
            source_id=photos_source.id,
            parent_id=None,
            name="photos",
            path="photos",
        )
        folder_year = AssetFolder(
            source_id=photos_source.id,
            parent_id=None,
            name="2024",
            path="photos/2024",
        )
        session.add_all([folder_root, folder_year])
        session.flush()
        folder_year.parent_id = folder_root.id

        folder_trip = AssetFolder(
            source_id=photos_source.id,
            parent_id=folder_year.id,
            name="Trip",
            path="photos/2024/Trip",
        )
        folder_home = AssetFolder(
            source_id=photos_source.id,
            parent_id=folder_year.id,
            name="Home",
            path="photos/2024/Home",
        )
        session.add_all([folder_trip, folder_home])
        session.flush()

        collection_portraits = AssetCollection(
            source_id=lightroom_source.id,
            parent_id=None,
            name="Portraits",
            path="Portraits",
            external_id="portraits",
            collection_type="collection",
            metadata_json=None,
        )
        collection_trips = AssetCollection(
            source_id=lightroom_source.id,
            parent_id=None,
            name="Trips",
            path="Trips",
            external_id="trips",
            collection_type="collection",
            metadata_json=None,
        )
        session.add_all([collection_portraits, collection_trips])
        session.flush()
        collection_italy = AssetCollection(
            source_id=lightroom_source.id,
            parent_id=collection_trips.id,
            name="Italy",
            path="Trips/Italy",
            external_id="trips:italy",
            collection_type="collection",
            metadata_json=None,
        )
        session.add(collection_italy)
        session.flush()

        photo_assets = [
            Asset(
                short_id="PHOT0001",
                source_id=photos_source.id,
                external_id="/library/photos/2024/Trip/venice-anna.jpg",
                media_type="photo",
                timestamp=_timestamp(2024, 7, 5, 10),
                summary=None,
                latitude=None,
                longitude=None,
                folder_id=folder_trip.id,
                metadata_json={"filename": "venice-anna.jpg"},
            ),
            Asset(
                short_id="PHOT0002",
                source_id=photos_source.id,
                external_id="/library/photos/2024/Trip/venice-evening.jpg",
                media_type="photo",
                timestamp=_timestamp(2024, 7, 6, 12),
                summary="Evening Walk",
                latitude=None,
                longitude=None,
                folder_id=folder_trip.id,
                metadata_json={"filename": "venice-evening.jpg"},
            ),
            Asset(
                short_id="PHOT0003",
                source_id=photos_source.id,
                external_id="/library/photos/2024/Home/family-home.jpg",
                media_type="photo",
                timestamp=_timestamp(2024, 7, 7, 8),
                summary=None,
                latitude=None,
                longitude=None,
                folder_id=folder_home.id,
                metadata_json={"filename": "family-home.jpg"},
            ),
        ]
        lightroom_assets = [
            Asset(
                short_id="LR000004",
                source_id=lightroom_source.id,
                external_id="lr:portrait-1",
                media_type="photo",
                timestamp=_timestamp(2024, 8, 1, 9),
                summary=None,
                latitude=None,
                longitude=None,
                folder_id=None,
                metadata_json={"file_name": "portrait-anna.jpg", "face_regions": []},
            ),
            Asset(
                short_id="LR000005",
                source_id=lightroom_source.id,
                external_id="lr:trip-italy-1",
                media_type="photo",
                timestamp=_timestamp(2024, 8, 2, 11),
                summary=None,
                latitude=46.5833,
                longitude=12.2,
                folder_id=None,
                creator_person_id=anna.id,
                metadata_json={
                    "file_name": "italy-lake.jpg",
                    "preserved_filename": "italy-lake-original.jpg",
                    "caption": "Dolomites lakeside in morning light.",
                    "description": "A quiet stop before the next trail.",
                    "camera": "Canon EOS R5",
                    "lens": "RF24-70mm F2.8 L IS USM",
                    "aperture_f_number": 2.8,
                    "shutter_speed_seconds": 0.005,
                    "focal_length_mm": 35.0,
                    "iso": 400,
                    "face_regions": [
                        {
                            "name": "Anna Becker",
                            "left": 0.22,
                            "top": 0.14,
                            "right": 0.43,
                            "bottom": 0.51,
                        },
                        {
                            "name": "",
                            "left": 0.6,
                            "top": 0.2,
                            "right": 0.75,
                            "bottom": 0.42,
                        },
                        {
                            "name": "Rejected Person",
                            "left": 0.1,
                            "top": 0.6,
                            "right": 0.25,
                            "bottom": 0.82,
                            "confirmed": False,
                        },
                    ],
                },
            ),
        ]
        session.add_all([*photo_assets, *lightroom_assets])
        session.flush()

        session.add_all(
            [
                AssetPerson(asset_id=photo_assets[0].id, person_id=anna.id),
                AssetPerson(asset_id=photo_assets[1].id, person_id=milo.id),
                AssetPerson(asset_id=photo_assets[2].id, person_id=anna.id),
                AssetPerson(asset_id=lightroom_assets[0].id, person_id=anna.id),
                AssetPerson(asset_id=lightroom_assets[1].id, person_id=anna.id),
            ]
        )
        session.add_all(
            [
                AssetTag(asset_id=photo_assets[0].id, tag_id=italy_tag.id),
                AssetTag(asset_id=photo_assets[1].id, tag_id=travel_tag.id),
                AssetTag(asset_id=photo_assets[2].id, tag_id=home_tag.id),
                AssetTag(asset_id=lightroom_assets[0].id, tag_id=home_tag.id),
                AssetTag(asset_id=lightroom_assets[1].id, tag_id=italy_tag.id),
            ]
        )
        session.add_all(
            [
                AssetCollectionItem(
                    collection_id=collection_portraits.id,
                    asset_id=lightroom_assets[0].id,
                ),
                AssetCollectionItem(
                    collection_id=collection_trips.id,
                    asset_id=lightroom_assets[1].id,
                ),
                AssetCollectionItem(
                    collection_id=collection_italy.id,
                    asset_id=lightroom_assets[1].id,
                ),
            ]
        )
        session.commit()


def _create_runtime(*, workspace_root: Path):
    database_path = workspace_root / "pixelpast.db"
    settings = Settings(database_url=f"sqlite:///{database_path.as_posix()}")
    runtime = create_runtime_context(settings=settings)
    initialize_database(runtime)
    return runtime


def _timestamp(year: int, month: int, day: int, hour: int) -> datetime:
    return datetime(year, month, day, hour, 0, 0, tzinfo=UTC)


def _create_workspace_dir(*, prefix: str) -> Path:
    workspace_root = Path("var") / f"{prefix}-{uuid4().hex}"
    workspace_root.mkdir(parents=True, exist_ok=False)
    return workspace_root
