"""Integration tests for the social-graph API contract."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from pixelpast.api.app import create_app
from pixelpast.persistence.models import Asset, AssetPerson, Person
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import Settings


def test_social_graph_endpoint_returns_stable_response_shape() -> None:
    workspace_root = _create_workspace_dir(prefix="social-graph-shape")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        _seed_social_graph_scenario(runtime=runtime)

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get("/api/social/graph?start=2024-01-02&end=2024-01-03")

        assert response.status_code == 200
        assert response.json() == {
            "persons": [
                {"id": 1, "name": "Anna", "occurrence_count": 2},
                {"id": 2, "name": "Ben", "occurrence_count": 2},
                {"id": 3, "name": "Zoe", "occurrence_count": 1},
            ],
            "links": [
                {"person_ids": [1, 2], "weight": 2},
                {"person_ids": [1, 3], "weight": 1},
                {"person_ids": [2, 3], "weight": 1},
            ],
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_social_graph_endpoint_returns_empty_graph_when_no_assets_qualify() -> None:
    workspace_root = _create_workspace_dir(prefix="social-graph-empty")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        app = create_app(settings=runtime.settings)

        with TestClient(app) as client:
            response = client.get("/api/social/graph?start=2024-01-01&end=2024-01-31")

        assert response.status_code == 200
        assert response.json() == {"persons": [], "links": []}
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_social_graph_endpoint_supports_person_filter_over_qualifying_assets() -> None:
    workspace_root = _create_workspace_dir(prefix="social-graph-person-filter")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        _seed_social_graph_scenario(runtime=runtime)

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get(
                "/api/social/graph?start=2024-01-02&end=2024-01-03&person_ids=1"
            )

        assert response.status_code == 200
        assert response.json() == {
            "persons": [
                {"id": 1, "name": "Anna", "occurrence_count": 2},
                {"id": 2, "name": "Ben", "occurrence_count": 2},
                {"id": 3, "name": "Zoe", "occurrence_count": 1},
            ],
            "links": [
                {"person_ids": [1, 2], "weight": 2},
                {"person_ids": [1, 3], "weight": 1},
                {"person_ids": [2, 3], "weight": 1},
            ],
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_social_graph_endpoint_rejects_unsupported_persistent_filters() -> None:
    workspace_root = _create_workspace_dir(prefix="social-graph-unsupported-filters")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        app = create_app(settings=runtime.settings)

        with TestClient(app) as client:
            response = client.get("/api/social/graph?tag_paths=travel/europe")

        assert response.status_code == 400
        assert response.json() == {
            "detail": (
                "unsupported social graph filters: tag_paths; "
                "supported filters: start, end, person_ids"
            )
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def _seed_social_graph_scenario(*, runtime) -> None:
    with runtime.session_factory() as session:
        anna = Person(name="Anna", aliases=None, metadata_json=None)
        ben = Person(name="Ben", aliases=None, metadata_json=None)
        zoe = Person(name="Zoe", aliases=None, metadata_json=None)
        session.add_all([anna, ben, zoe])
        session.flush()

        asset_one = Asset(
            external_id="asset-1",
            media_type="photo",
            timestamp=datetime(2024, 1, 2, 9, 0, tzinfo=UTC),
            summary=None,
            latitude=None,
            longitude=None,
            creator_person_id=None,
            metadata_json={},
        )
        asset_two = Asset(
            external_id="asset-2",
            media_type="photo",
            timestamp=datetime(2024, 1, 3, 9, 0, tzinfo=UTC),
            summary=None,
            latitude=None,
            longitude=None,
            creator_person_id=None,
            metadata_json={},
        )
        asset_three = Asset(
            external_id="asset-3",
            media_type="photo",
            timestamp=datetime(2024, 1, 4, 9, 0, tzinfo=UTC),
            summary=None,
            latitude=None,
            longitude=None,
            creator_person_id=None,
            metadata_json={},
        )
        session.add_all([asset_one, asset_two, asset_three])
        session.flush()

        session.add_all(
            [
                AssetPerson(asset_id=asset_one.id, person_id=anna.id),
                AssetPerson(asset_id=asset_one.id, person_id=ben.id),
                AssetPerson(asset_id=asset_two.id, person_id=anna.id),
                AssetPerson(asset_id=asset_two.id, person_id=ben.id),
                AssetPerson(asset_id=asset_two.id, person_id=zoe.id),
                AssetPerson(asset_id=asset_three.id, person_id=ben.id),
            ]
        )
        session.commit()


def _create_runtime(*, workspace_root: Path):
    database_path = workspace_root / "pixelpast.db"
    settings = Settings(database_url=f"sqlite:///{database_path.as_posix()}")
    runtime = create_runtime_context(settings=settings)
    initialize_database(runtime)
    return runtime


def _create_workspace_dir(*, prefix: str) -> Path:
    workspace_root = Path("var") / f"{prefix}-{uuid4().hex}"
    workspace_root.mkdir(parents=True, exist_ok=False)
    return workspace_root
