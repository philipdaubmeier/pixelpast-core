"""Integration tests for heatmap and day-detail API endpoints."""

from __future__ import annotations

import shutil
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from pixelpast.api.app import create_app
from pixelpast.persistence.models import (
    Asset,
    AssetPerson,
    AssetTag,
    DailyAggregate,
    Event,
    EventPerson,
    EventTag,
    Person,
    Source,
    Tag,
)
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import Settings


def test_exploration_endpoint_returns_current_year_dense_grid_when_empty() -> None:
    workspace_root = _create_workspace_dir(prefix="timeline-api-exploration-empty")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        app = create_app(settings=runtime.settings)

        with TestClient(app) as client:
            response = client.get("/api/exploration")

        assert response.status_code == 200
        payload = response.json()
        current_year = date.today().year
        day_count = (date(current_year + 1, 1, 1) - date(current_year, 1, 1)).days
        assert payload["range"] == {
            "start": f"{current_year}-01-01",
            "end": f"{current_year}-12-31",
        }
        assert payload["view_modes"] == [
            {
                "id": "activity",
                "label": "Activity",
                "description": "Default heat intensity across all timeline sources.",
            },
            {
                "id": "travel",
                "label": "Travel",
                "description": "Highlights movement-heavy and location-rich days.",
            },
            {
                "id": "sports",
                "label": "Sports",
                "description": "Reserves the grid for workout and fitness projections.",
            },
            {
                "id": "party_probability",
                "label": "Social",
                "description": (
                    "Placeholder derived view for future social-density signals."
                ),
            },
        ]
        assert payload["persons"] == []
        assert payload["tags"] == []
        assert len(payload["days"]) == day_count
        assert payload["days"][0] == {
            "date": f"{current_year}-01-01",
            "event_count": 0,
            "asset_count": 0,
            "activity_score": 0,
            "color_value": "empty",
            "has_data": False,
            "person_ids": [],
            "tag_paths": [],
        }
        assert payload["days"][-1]["date"] == f"{current_year}-12-31"
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_exploration_endpoint_returns_dense_days_catalog_without_taxonomy_logic(
) -> None:
    workspace_root = _create_workspace_dir(prefix="timeline-api-exploration-range")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)

        with runtime.session_factory() as session:
            source = Source(name="Calendar", type="calendar", config={})
            anna = Person(
                name="Anna",
                aliases=None,
                metadata_json={"role": "Family"},
            )
            milo = Person(
                name="Milo",
                aliases=None,
                metadata_json={"role": "Travel buddy"},
            )
            project_tag = Tag(
                label="Project Apollo",
                path="projects/apollo",
                metadata_json=None,
            )
            family_tag = Tag(
                label="Family Anna",
                path="family/anna",
                metadata_json=None,
            )
            mood_tag = Tag(
                label="Focused",
                path="mood/focused",
                metadata_json=None,
            )
            session.add_all([source, anna, milo, project_tag, family_tag, mood_tag])
            session.flush()

            day_two_event = Event(
                source_id=source.id,
                type="calendar",
                timestamp_start=datetime(2024, 1, 2, 10, 0, tzinfo=UTC),
                timestamp_end=None,
                title="Planning",
                summary=None,
                latitude=None,
                longitude=None,
                raw_payload={},
                derived_payload={},
            )
            day_two_asset = Asset(
                external_id="asset-1",
                media_type="photo",
                timestamp=datetime(2024, 1, 2, 12, 0, tzinfo=UTC),
                latitude=None,
                longitude=None,
                metadata_json={},
            )
            day_three_event = Event(
                source_id=source.id,
                type="calendar",
                timestamp_start=datetime(2024, 1, 3, 8, 0, tzinfo=UTC),
                timestamp_end=None,
                title="Run",
                summary=None,
                latitude=None,
                longitude=None,
                raw_payload={},
                derived_payload={},
            )
            session.add_all([day_two_event, day_two_asset, day_three_event])
            session.flush()

            session.add_all(
                [
                    EventPerson(event_id=day_two_event.id, person_id=anna.id),
                    AssetPerson(asset_id=day_two_asset.id, person_id=milo.id),
                    EventTag(event_id=day_two_event.id, tag_id=project_tag.id),
                    AssetTag(asset_id=day_two_asset.id, tag_id=family_tag.id),
                    EventTag(event_id=day_three_event.id, tag_id=mood_tag.id),
                    DailyAggregate(
                        date=date(2024, 1, 2),
                        total_events=1,
                        media_count=1,
                        activity_score=40,
                        metadata_json={"score_version": "v1"},
                    ),
                ]
            )
            session.commit()

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get("/api/exploration?start=2024-01-01&end=2024-01-03")

        assert response.status_code == 200
        assert response.json() == {
            "range": {
                "start": "2024-01-01",
                "end": "2024-01-03",
            },
            "view_modes": [
                {
                    "id": "activity",
                    "label": "Activity",
                    "description": (
                        "Default heat intensity across all timeline sources."
                    ),
                },
                {
                    "id": "travel",
                    "label": "Travel",
                    "description": "Highlights movement-heavy and location-rich days.",
                },
                {
                    "id": "sports",
                    "label": "Sports",
                    "description": (
                        "Reserves the grid for workout and fitness projections."
                    ),
                },
                {
                    "id": "party_probability",
                    "label": "Social",
                    "description": (
                        "Placeholder derived view for future social-density signals."
                    ),
                },
            ],
            "persons": [
                {
                    "id": 1,
                    "name": "Anna",
                    "role": "Family",
                },
                {
                    "id": 2,
                    "name": "Milo",
                    "role": "Travel buddy",
                },
            ],
            "tags": [
                {
                    "path": "family/anna",
                    "label": "Family Anna",
                },
                {
                    "path": "mood/focused",
                    "label": "Focused",
                },
                {
                    "path": "projects/apollo",
                    "label": "Project Apollo",
                },
            ],
            "days": [
                {
                    "date": "2024-01-01",
                    "event_count": 0,
                    "asset_count": 0,
                    "activity_score": 0,
                    "color_value": "empty",
                    "has_data": False,
                    "person_ids": [],
                    "tag_paths": [],
                },
                {
                    "date": "2024-01-02",
                    "event_count": 1,
                    "asset_count": 1,
                    "activity_score": 40,
                    "color_value": "medium",
                    "has_data": True,
                    "person_ids": [1, 2],
                    "tag_paths": ["family/anna", "projects/apollo"],
                },
                {
                    "date": "2024-01-03",
                    "event_count": 1,
                    "asset_count": 0,
                    "activity_score": 1,
                    "color_value": "low",
                    "has_data": True,
                    "person_ids": [],
                    "tag_paths": ["mood/focused"],
                },
            ],
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_exploration_endpoint_resolves_available_timeline_and_pads_years() -> None:
    workspace_root = _create_workspace_dir(prefix="timeline-api-exploration-bounds")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)

        with runtime.session_factory() as session:
            source = Source(name="Calendar", type="calendar", config={})
            session.add(source)
            session.flush()
            session.add_all(
                [
                    Event(
                        source_id=source.id,
                        type="calendar",
                        timestamp_start=datetime(2024, 5, 10, 9, 0, tzinfo=UTC),
                        timestamp_end=None,
                        title="Trip planning",
                        summary=None,
                        latitude=None,
                        longitude=None,
                        raw_payload={},
                        derived_payload={},
                    ),
                    Asset(
                        external_id="asset-1",
                        media_type="photo",
                        timestamp=datetime(2025, 2, 3, 18, 0, tzinfo=UTC),
                        latitude=None,
                        longitude=None,
                        metadata_json={},
                    ),
                ]
            )
            session.commit()

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get("/api/exploration")

        assert response.status_code == 200
        payload = response.json()
        assert payload["range"] == {
            "start": "2024-01-01",
            "end": "2025-12-31",
        }
        assert len(payload["days"]) == 731

        day_by_date = {day["date"]: day for day in payload["days"]}
        assert day_by_date["2024-05-10"] == {
            "date": "2024-05-10",
            "event_count": 1,
            "asset_count": 0,
            "activity_score": 1,
            "color_value": "low",
            "has_data": True,
            "person_ids": [],
            "tag_paths": [],
        }
        assert day_by_date["2025-02-03"] == {
            "date": "2025-02-03",
            "event_count": 0,
            "asset_count": 1,
            "activity_score": 1,
            "color_value": "low",
            "has_data": True,
            "person_ids": [],
            "tag_paths": [],
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_exploration_endpoint_rejects_partial_explicit_range() -> None:
    workspace_root = _create_workspace_dir(prefix="timeline-api-exploration-partial")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        app = create_app(settings=runtime.settings)

        with TestClient(app) as client:
            response = client.get("/api/exploration?start=2024-01-01")

        assert response.status_code == 400
        assert response.json() == {
            "detail": "start and end must both be provided together",
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_demo_exploration_endpoint_returns_deterministic_multi_year_payload() -> None:
    workspace_root = _create_workspace_dir(prefix="timeline-api-demo-exploration")
    try:
        settings = _create_demo_settings(workspace_root=workspace_root)
        app_one = create_app(settings=settings)
        app_two = create_app(settings=settings)

        with TestClient(app_one) as client_one:
            first_response = client_one.get("/api/exploration")
            second_response = client_one.get("/api/exploration")

        with TestClient(app_two) as client_two:
            third_response = client_two.get("/api/exploration")

        assert first_response.status_code == 200
        assert second_response.status_code == 200
        assert third_response.status_code == 200
        assert first_response.json() == second_response.json() == third_response.json()

        payload = first_response.json()
        assert payload["range"] == {
            "start": "2021-01-01",
            "end": "2026-12-31",
        }
        assert len(payload["days"]) == 2191
        assert len({day["date"][:4] for day in payload["days"]}) == 6
        assert payload["persons"] == [
            {"id": 1, "name": "Anna", "role": "Family"},
            {"id": 5, "name": "Emma", "role": "Friend"},
            {"id": 3, "name": "Luca", "role": "Work"},
            {"id": 2, "name": "Milo", "role": "Travel buddy"},
            {"id": 4, "name": "Nora", "role": "Coach"},
        ]
        assert payload["tags"] == [
            {"path": "activity/outdoors", "label": "Outdoors"},
            {"path": "activity/sports/running", "label": "Running"},
            {"path": "people/family", "label": "Family"},
            {"path": "social/house-party", "label": "House Party"},
            {"path": "travel/europe", "label": "Europe"},
            {"path": "travel/weekender", "label": "Weekend Escape"},
            {"path": "work/project-atlas", "label": "Project Atlas"},
        ]
        assert any(
            any(tag_path.startswith("travel/") for tag_path in day["tag_paths"])
            for day in payload["days"]
        )
        assert any(
            any(tag_path.startswith("activity/") for tag_path in day["tag_paths"])
            for day in payload["days"]
        )
        assert any(len(day["person_ids"]) >= 2 for day in payload["days"])
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


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


def test_exploration_endpoint_allows_local_ui_origin_via_cors() -> None:
    workspace_root = _create_workspace_dir(prefix="timeline-api-cors")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        app = create_app(settings=runtime.settings)

        with TestClient(app) as client:
            response = client.options(
                "/api/exploration",
                headers={
                    "Origin": "http://localhost:5173",
                    "Access-Control-Request-Method": "GET",
                },
            )

        assert response.status_code == 200
        assert (
            response.headers["access-control-allow-origin"]
            == "http://localhost:5173"
        )
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_day_context_endpoint_returns_dense_mixed_context_range() -> None:
    workspace_root = _create_workspace_dir(prefix="timeline-api-day-context-mixed")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)

        with runtime.session_factory() as session:
            source = Source(name="Calendar", type="calendar", config={})
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
                    anna,
                    ben,
                    milo,
                    project_tag,
                    travel_tag,
                    family_tag,
                ]
            )
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
                external_id="asset-museum",
                media_type="photo",
                timestamp=datetime(2024, 1, 2, 10, 30, tzinfo=UTC),
                latitude=48.8566,
                longitude=2.3522,
                metadata_json={"label": "Museum"},
            )
            mixed_asset_unlabeled = Asset(
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
                            "id": "event:1",
                            "label": "City walk",
                            "latitude": 52.52,
                            "longitude": 13.405,
                        },
                        {
                            "id": "asset:1",
                            "label": "Museum",
                            "latitude": 48.8566,
                            "longitude": 2.3522,
                        },
                        {
                            "id": "asset:2",
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
                            "id": "asset:3",
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


def test_heatmap_endpoint_returns_empty_range() -> None:
    workspace_root = _create_workspace_dir(prefix="timeline-api-heatmap-empty")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        app = create_app(settings=runtime.settings)

        with TestClient(app) as client:
            response = client.get("/api/heatmap?start=2024-01-01&end=2024-01-03")

        assert response.status_code == 200
        assert response.json() == {
            "start": "2024-01-01",
            "end": "2024-01-03",
            "days": [],
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_heatmap_endpoint_returns_daily_aggregates_in_range_order() -> None:
    workspace_root = _create_workspace_dir(prefix="timeline-api-heatmap-data")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)

        with runtime.session_factory() as session:
            session.add_all(
                [
                    DailyAggregate(
                        date=date(2024, 1, 1),
                        total_events=1,
                        media_count=0,
                        activity_score=1,
                        metadata_json={"score_version": "v1"},
                    ),
                    DailyAggregate(
                        date=date(2024, 1, 2),
                        total_events=2,
                        media_count=1,
                        activity_score=3,
                        metadata_json={"score_version": "v1"},
                    ),
                    DailyAggregate(
                        date=date(2024, 1, 4),
                        total_events=0,
                        media_count=2,
                        activity_score=2,
                        metadata_json={"score_version": "v1"},
                    ),
                ]
            )
            session.commit()

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get("/api/heatmap?start=2024-01-02&end=2024-01-04")

        assert response.status_code == 200
        assert response.json() == {
            "start": "2024-01-02",
            "end": "2024-01-04",
            "days": [
                {
                    "date": "2024-01-02",
                    "total_events": 2,
                    "media_count": 1,
                    "activity_score": 3,
                },
                {
                    "date": "2024-01-04",
                    "total_events": 0,
                    "media_count": 2,
                    "activity_score": 2,
                },
            ],
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_heatmap_endpoint_rejects_invalid_range() -> None:
    workspace_root = _create_workspace_dir(prefix="timeline-api-heatmap-invalid")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        app = create_app(settings=runtime.settings)

        with TestClient(app) as client:
            response = client.get("/api/heatmap?start=2024-01-03&end=2024-01-01")

        assert response.status_code == 400
        assert response.json() == {
            "detail": "start must be less than or equal to end",
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
        session.add(source)
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

