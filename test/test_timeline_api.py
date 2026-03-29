"""Integration tests for day-context and day-detail API endpoints."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from pixelpast.api.app import create_app
from pixelpast.analytics.daily_views import build_default_daily_view_metadata
from pixelpast.persistence.models import (
    Asset,
    AssetPerson,
    AssetTag,
    DailyAggregate,
    DailyView,
    Event,
    EventPerson,
    EventTag,
    Person,
    Source,
    Tag,
)
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import Settings


def test_day_context_endpoint_returns_dense_empty_range() -> None:
    workspace_root = _create_workspace_dir(prefix="timeline-api-day-context-empty")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        app = create_app(settings=runtime.settings)

        with TestClient(app) as client:
            response = client.get("/api/days/context?start=2024-01-01&end=2024-01-03")

        assert response.status_code == 200
        assert response.json() == {
            "range": {
                "start": "2024-01-01",
                "end": "2024-01-03",
            },
            "days": [
                {
                    "date": "2024-01-01",
                    "persons": [],
                    "tags": [],
                    "map_points": [],
                    "summary_counts": {
                        "events": 0,
                        "assets": 0,
                        "places": 0,
                    },
                },
                {
                    "date": "2024-01-02",
                    "persons": [],
                    "tags": [],
                    "map_points": [],
                    "summary_counts": {
                        "events": 0,
                        "assets": 0,
                        "places": 0,
                    },
                },
                {
                    "date": "2024-01-03",
                    "persons": [],
                    "tags": [],
                    "map_points": [],
                    "summary_counts": {
                        "events": 0,
                        "assets": 0,
                        "places": 0,
                    },
                },
            ],
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_demo_day_context_endpoint_returns_dense_range_with_real_coordinates() -> None:
    workspace_root = _create_workspace_dir(prefix="timeline-api-demo-day-context")
    try:
        settings = _create_demo_settings(workspace_root=workspace_root)
        app = create_app(settings=settings)

        with TestClient(app) as client:
            first_response = client.get(
                "/api/days/context?start=2024-01-01&end=2024-01-31"
            )
            second_response = client.get(
                "/api/days/context?start=2024-01-01&end=2024-01-31"
            )

        assert first_response.status_code == 200
        assert second_response.status_code == 200
        assert first_response.json() == second_response.json()

        payload = first_response.json()
        assert payload["range"] == {
            "start": "2024-01-01",
            "end": "2024-01-31",
        }
        assert len(payload["days"]) == 31
        assert payload["days"][0]["date"] == "2024-01-01"
        assert payload["days"][-1]["date"] == "2024-01-31"
        assert any(day["persons"] for day in payload["days"])
        assert any(day["tags"] for day in payload["days"])
        assert any(day["map_points"] for day in payload["days"])

        first_mapped_day = next(
            day for day in payload["days"] if day["map_points"]
        )
        first_map_point = first_mapped_day["map_points"][0]
        assert sorted(first_map_point) == ["id", "label", "latitude", "longitude"]
        assert -90 <= first_map_point["latitude"] <= 90
        assert -180 <= first_map_point["longitude"] <= 180
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_day_context_endpoint_returns_dense_mixed_context_range() -> None:
    workspace_root = _create_workspace_dir(prefix="timeline-api-day-context-mixed")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)

        with runtime.session_factory() as session:
            source = Source(name="Calendar", type="calendar", config={})
            photo_source = Source(name="Photos", type="photos", config={})
            anna = Person(
                name="Anna",
                aliases=None,
                metadata_json={"role": "Family"},
            )
            ben = Person(
                name="Ben",
                aliases=None,
                metadata_json={"role": "Friend"},
            )
            milo = Person(
                name="Milo",
                aliases=None,
                metadata_json=None,
            )
            project_tag = Tag(
                label="Project Apollo",
                path="projects/apollo",
                metadata_json=None,
            )
            travel_tag = Tag(
                label="Travel",
                path="travel",
                metadata_json=None,
            )
            family_tag = Tag(
                label="Family",
                path="people/family",
                metadata_json=None,
            )
            session.add_all(
                [
                    source,
                    photo_source,
                    anna,
                    ben,
                    milo,
                    project_tag,
                    travel_tag,
                    family_tag,
                ]
            )
            session.flush()
            overall_view = DailyView(
                aggregate_scope="overall",
                source_type=None,
                label="Activity",
                description="Default heat intensity across all timeline sources.",
                metadata_json=build_default_daily_view_metadata(),
            )
            session.add(overall_view)
            session.flush()

            mixed_event = Event(
                source_id=source.id,
                type="calendar",
                timestamp_start=datetime(2024, 1, 2, 9, 0, tzinfo=UTC),
                timestamp_end=None,
                title="City walk",
                summary=None,
                latitude=52.52,
                longitude=13.405,
                raw_payload={},
                derived_payload={},
            )
            mixed_asset = Asset(
                source_id=photo_source.id,
                external_id="asset-museum",
                media_type="photo",
                timestamp=datetime(2024, 1, 2, 10, 30, tzinfo=UTC),
                latitude=48.8566,
                longitude=2.3522,
                metadata_json={"label": "Museum"},
            )
            mixed_asset_unlabeled = Asset(
                source_id=photo_source.id,
                external_id="asset-unlabeled",
                media_type="photo",
                timestamp=datetime(2024, 1, 2, 11, 0, tzinfo=UTC),
                latitude=41.9028,
                longitude=12.4964,
                metadata_json={},
            )
            event_only_day = Event(
                source_id=source.id,
                type="music_play",
                timestamp_start=datetime(2024, 1, 3, 8, 0, tzinfo=UTC),
                timestamp_end=None,
                title="Morning playlist",
                summary=None,
                latitude=None,
                longitude=None,
                raw_payload={},
                derived_payload={},
            )
            asset_only_day = Asset(
                source_id=photo_source.id,
                external_id="asset-day-four",
                media_type="video",
                timestamp=datetime(2024, 1, 4, 15, 45, tzinfo=UTC),
                latitude=40.7128,
                longitude=-74.006,
                metadata_json={},
            )
            session.add_all(
                [
                    mixed_event,
                    mixed_asset,
                    mixed_asset_unlabeled,
                    event_only_day,
                    asset_only_day,
                ]
            )
            session.flush()

            session.add_all(
                [
                    EventPerson(event_id=mixed_event.id, person_id=anna.id),
                    AssetPerson(asset_id=mixed_asset.id, person_id=ben.id),
                    AssetPerson(asset_id=mixed_asset_unlabeled.id, person_id=anna.id),
                    EventPerson(event_id=event_only_day.id, person_id=anna.id),
                    AssetPerson(asset_id=asset_only_day.id, person_id=milo.id),
                    EventTag(event_id=mixed_event.id, tag_id=project_tag.id),
                    AssetTag(asset_id=mixed_asset.id, tag_id=travel_tag.id),
                    AssetTag(asset_id=mixed_asset_unlabeled.id, tag_id=project_tag.id),
                    EventTag(event_id=event_only_day.id, tag_id=travel_tag.id),
                    AssetTag(asset_id=asset_only_day.id, tag_id=family_tag.id),
                    DailyAggregate(
                        date=datetime(2024, 1, 2, tzinfo=UTC).date(),
                        daily_view_id=overall_view.id,
                        total_events=1,
                        media_count=2,
                        activity_score=3,
                        tag_summary_json=[
                            {"path": "projects/apollo", "label": "Project Apollo", "count": 2},
                            {"path": "travel", "label": "Travel", "count": 1},
                        ],
                        person_summary_json=[
                            {"person_id": 1, "name": "Anna", "role": "Family", "count": 2},
                            {"person_id": 2, "name": "Ben", "role": "Friend", "count": 1},
                        ],
                        location_summary_json=[
                            {"label": "City walk", "latitude": 52.52, "longitude": 13.405, "count": 1},
                            {"label": "Museum", "latitude": 48.8566, "longitude": 2.3522, "count": 1},
                            {"label": "asset-unlabeled", "latitude": 41.9028, "longitude": 12.4964, "count": 1},
                        ],
                    ),
                    DailyAggregate(
                        date=datetime(2024, 1, 3, tzinfo=UTC).date(),
                        daily_view_id=overall_view.id,
                        total_events=1,
                        media_count=0,
                        activity_score=1,
                        tag_summary_json=[
                            {"path": "travel", "label": "Travel", "count": 1}
                        ],
                        person_summary_json=[
                            {"person_id": 1, "name": "Anna", "role": "Family", "count": 1}
                        ],
                        location_summary_json=[],
                    ),
                    DailyAggregate(
                        date=datetime(2024, 1, 4, tzinfo=UTC).date(),
                        daily_view_id=overall_view.id,
                        total_events=0,
                        media_count=1,
                        activity_score=1,
                        tag_summary_json=[
                            {"path": "people/family", "label": "Family", "count": 1}
                        ],
                        person_summary_json=[
                            {"person_id": 3, "name": "Milo", "role": None, "count": 1}
                        ],
                        location_summary_json=[
                            {"label": "asset-day-four", "latitude": 40.7128, "longitude": -74.006, "count": 1}
                        ],
                    ),
                ]
            )
            session.commit()

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get("/api/days/context?start=2024-01-01&end=2024-01-04")

        assert response.status_code == 200
        assert response.json() == {
            "range": {
                "start": "2024-01-01",
                "end": "2024-01-04",
            },
            "days": [
                {
                    "date": "2024-01-01",
                    "persons": [],
                    "tags": [],
                    "map_points": [],
                    "summary_counts": {
                        "events": 0,
                        "assets": 0,
                        "places": 0,
                    },
                },
                {
                    "date": "2024-01-02",
                    "persons": [
                        {
                            "id": 1,
                            "name": "Anna",
                            "role": "Family",
                        },
                        {
                            "id": 2,
                            "name": "Ben",
                            "role": "Friend",
                        },
                    ],
                    "tags": [
                        {
                            "path": "projects/apollo",
                            "label": "Project Apollo",
                        },
                        {
                            "path": "travel",
                            "label": "Travel",
                        },
                    ],
                    "map_points": [
                        {
                            "id": "location:2024-01-02:1",
                            "label": "City walk",
                            "latitude": 52.52,
                            "longitude": 13.405,
                        },
                        {
                            "id": "location:2024-01-02:2",
                            "label": "Museum",
                            "latitude": 48.8566,
                            "longitude": 2.3522,
                        },
                        {
                            "id": "location:2024-01-02:3",
                            "label": "asset-unlabeled",
                            "latitude": 41.9028,
                            "longitude": 12.4964,
                        },
                    ],
                    "summary_counts": {
                        "events": 1,
                        "assets": 2,
                        "places": 3,
                    },
                },
                {
                    "date": "2024-01-03",
                    "persons": [
                        {
                            "id": 1,
                            "name": "Anna",
                            "role": "Family",
                        },
                    ],
                    "tags": [
                        {
                            "path": "travel",
                            "label": "Travel",
                        },
                    ],
                    "map_points": [],
                    "summary_counts": {
                        "events": 1,
                        "assets": 0,
                        "places": 0,
                    },
                },
                {
                    "date": "2024-01-04",
                    "persons": [
                        {
                            "id": 3,
                            "name": "Milo",
                            "role": None,
                        },
                    ],
                    "tags": [
                        {
                            "path": "people/family",
                            "label": "Family",
                        },
                    ],
                    "map_points": [
                        {
                            "id": "location:2024-01-04:1",
                            "label": "asset-day-four",
                            "latitude": 40.7128,
                            "longitude": -74.006,
                        },
                    ],
                    "summary_counts": {
                        "events": 0,
                        "assets": 1,
                        "places": 1,
                    },
                },
            ],
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_day_context_endpoint_rejects_invalid_range() -> None:
    workspace_root = _create_workspace_dir(prefix="timeline-api-day-context-invalid")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        app = create_app(settings=runtime.settings)

        with TestClient(app) as client:
            response = client.get("/api/days/context?start=2024-01-04&end=2024-01-01")

        assert response.status_code == 400
        assert response.json() == {
            "detail": "start must be less than or equal to end",
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_day_context_endpoint_rejects_ranges_beyond_configured_limit() -> None:
    workspace_root = _create_workspace_dir(prefix="timeline-api-day-context-limit")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        limited_settings = runtime.settings.model_copy(
            update={"day_context_max_days": 2}
        )
        app = create_app(settings=limited_settings)

        with TestClient(app) as client:
            response = client.get("/api/days/context?start=2024-01-01&end=2024-01-03")

        assert response.status_code == 400
        assert response.json() == {
            "detail": "requested range exceeds maximum day context window of 2 days",
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_day_context_endpoint_keeps_unlabeled_map_coordinates() -> None:
    workspace_root = _create_workspace_dir(prefix="timeline-api-day-context-path")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)

        with runtime.session_factory() as session:
            overall_view = DailyView(
                aggregate_scope="overall",
                source_type=None,
                label="Activity",
                description="Default heat intensity across all timeline sources.",
                metadata_json=build_default_daily_view_metadata(),
            )
            session.add(overall_view)
            session.flush()
            session.add(
                DailyAggregate(
                    date=datetime(2024, 1, 2, tzinfo=UTC).date(),
                    daily_view_id=overall_view.id,
                    total_events=2,
                    media_count=0,
                    activity_score=4,
                    tag_summary_json=[],
                    person_summary_json=[],
                    location_summary_json=[
                        {"latitude": 52.52, "longitude": 13.405},
                        {"latitude": 52.521, "longitude": 13.406},
                        {"label": "Cafe", "latitude": 52.522, "longitude": 13.407, "count": 1},
                    ],
                )
            )
            session.commit()

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get("/api/days/context?start=2024-01-02&end=2024-01-02")

        assert response.status_code == 200
        assert response.json() == {
            "range": {
                "start": "2024-01-02",
                "end": "2024-01-02",
            },
            "days": [
                {
                    "date": "2024-01-02",
                    "persons": [],
                    "tags": [],
                    "map_points": [
                        {
                            "id": None,
                            "label": None,
                            "latitude": 52.52,
                            "longitude": 13.405,
                        },
                        {
                            "id": None,
                            "label": None,
                            "latitude": 52.521,
                            "longitude": 13.406,
                        },
                        {
                            "id": "location:2024-01-02:3",
                            "label": "Cafe",
                            "latitude": 52.522,
                            "longitude": 13.407,
                        },
                    ],
                    "summary_counts": {
                        "events": 2,
                        "assets": 0,
                        "places": 3,
                    },
                }
            ],
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_day_detail_endpoint_returns_events_only() -> None:
    workspace_root = _create_workspace_dir(prefix="timeline-api-day-events")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        _seed_timeline(
            runtime=runtime,
            events=[
                datetime(2024, 1, 2, 8, 30, tzinfo=UTC),
                datetime(2024, 1, 2, 11, 0, tzinfo=UTC),
            ],
            assets=[],
        )

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get("/api/days/2024-01-02")

        assert response.status_code == 200
        assert response.json() == {
            "date": "2024-01-02",
            "items": [
                {
                    "item_type": "event",
                    "id": 1,
                    "timestamp": "2024-01-02T08:30:00Z",
                    "event_type": "calendar",
                    "title": "Event 1",
                    "summary": None,
                },
                {
                    "item_type": "event",
                    "id": 2,
                    "timestamp": "2024-01-02T11:00:00Z",
                    "event_type": "calendar",
                    "title": "Event 2",
                    "summary": None,
                },
            ],
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_day_detail_endpoint_returns_empty_items_for_empty_day() -> None:
    workspace_root = _create_workspace_dir(prefix="timeline-api-day-empty")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        app = create_app(settings=runtime.settings)

        with TestClient(app) as client:
            response = client.get("/api/days/2024-01-02")

        assert response.status_code == 200
        assert response.json() == {
            "date": "2024-01-02",
            "items": [],
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_day_detail_endpoint_returns_assets_only() -> None:
    workspace_root = _create_workspace_dir(prefix="timeline-api-day-assets")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        _seed_timeline(
            runtime=runtime,
            events=[],
            assets=[
                datetime(2024, 1, 2, 9, 15, tzinfo=UTC),
                datetime(2024, 1, 2, 9, 45, tzinfo=UTC),
            ],
        )

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get("/api/days/2024-01-02")

        assert response.status_code == 200
        assert response.json() == {
            "date": "2024-01-02",
            "items": [
                {
                    "item_type": "asset",
                    "id": 1,
                    "timestamp": "2024-01-02T09:15:00Z",
                    "media_type": "photo",
                    "external_id": "asset-1",
                },
                {
                    "item_type": "asset",
                    "id": 2,
                    "timestamp": "2024-01-02T09:45:00Z",
                    "media_type": "photo",
                    "external_id": "asset-2",
                },
            ],
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_day_detail_endpoint_returns_mixed_items_in_timestamp_order() -> None:
    workspace_root = _create_workspace_dir(prefix="timeline-api-day-mixed")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        _seed_timeline(
            runtime=runtime,
            events=[
                datetime(2024, 1, 2, 8, 0, tzinfo=UTC),
                datetime(2024, 1, 2, 12, 0, tzinfo=UTC),
            ],
            assets=[
                datetime(2024, 1, 2, 9, 30, tzinfo=UTC),
                datetime(2024, 1, 2, 18, 15, tzinfo=UTC),
            ],
        )

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get("/api/days/2024-01-02")

        assert response.status_code == 200
        assert response.json() == {
            "date": "2024-01-02",
            "items": [
                {
                    "item_type": "event",
                    "id": 1,
                    "timestamp": "2024-01-02T08:00:00Z",
                    "event_type": "calendar",
                    "title": "Event 1",
                    "summary": None,
                },
                {
                    "item_type": "asset",
                    "id": 1,
                    "timestamp": "2024-01-02T09:30:00Z",
                    "media_type": "photo",
                    "external_id": "asset-1",
                },
                {
                    "item_type": "event",
                    "id": 2,
                    "timestamp": "2024-01-02T12:00:00Z",
                    "event_type": "calendar",
                    "title": "Event 2",
                    "summary": None,
                },
                {
                    "item_type": "asset",
                    "id": 2,
                    "timestamp": "2024-01-02T18:15:00Z",
                    "media_type": "photo",
                    "external_id": "asset-2",
                },
            ],
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def _seed_timeline(
    *,
    runtime,
    events: list[datetime],
    assets: list[datetime],
) -> None:
    with runtime.session_factory() as session:
        source = Source(name="Calendar", type="calendar", config={})
        photo_source = Source(name="Photos", type="photos", config={})
        session.add_all([source, photo_source])
        session.flush()

        for index, timestamp in enumerate(events, start=1):
            session.add(
                Event(
                    source_id=source.id,
                    type="calendar",
                    timestamp_start=timestamp,
                    timestamp_end=None,
                    title=f"Event {index}",
                    summary=None,
                    latitude=None,
                    longitude=None,
                    raw_payload={},
                    derived_payload={},
                )
            )

        for index, timestamp in enumerate(assets, start=1):
            session.add(
                Asset(
                    source_id=photo_source.id,
                    external_id=f"asset-{index}",
                    media_type="photo",
                    timestamp=timestamp,
                    latitude=None,
                    longitude=None,
                    metadata_json={},
                )
            )

        session.commit()

def _create_runtime(*, workspace_root: Path):
    database_path = workspace_root / "pixelpast.db"
    settings = Settings(database_url=f"sqlite:///{database_path.as_posix()}")
    runtime = create_runtime_context(settings=settings)
    initialize_database(runtime)
    return runtime


def _create_demo_settings(*, workspace_root: Path) -> Settings:
    database_path = workspace_root / "missing" / "pixelpast.db"
    return Settings(
        database_url=f"sqlite:///{database_path.as_posix()}",
        timeline_projection_provider="demo",
    )


def _create_workspace_dir(*, prefix: str) -> Path:
    workspace_root = Path("var") / f"{prefix}-{uuid4().hex}"
    workspace_root.mkdir(parents=True, exist_ok=False)
    return workspace_root

