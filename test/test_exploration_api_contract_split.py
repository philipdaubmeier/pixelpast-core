"""Integration tests for the split exploration API contracts."""

from __future__ import annotations

import shutil
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from pixelpast.api.app import create_app
from pixelpast.analytics.daily_views import build_default_daily_view_metadata
from pixelpast.persistence.models import (
    Asset,
    AssetPerson,
    AssetTag,
    DAILY_AGGREGATE_SCOPE_SOURCE_TYPE,
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


def test_exploration_bootstrap_endpoint_returns_current_year_shell_when_empty() -> None:
    workspace_root = _create_workspace_dir(prefix="exploration-bootstrap-empty")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        app = create_app(settings=runtime.settings)

        with TestClient(app) as client:
            response = client.get("/api/exploration/bootstrap")

        assert response.status_code == 200
        current_year = date.today().year
        assert response.json() == {
            "range": {
                "start": f"{current_year}-01-01",
                "end": f"{current_year}-12-31",
            },
            "view_modes": _fallback_view_modes_payload(),
            "persons": [],
            "tags": [],
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_exploration_grid_endpoint_returns_current_year_dense_grid_when_empty() -> None:
    workspace_root = _create_workspace_dir(prefix="exploration-grid-empty")
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
        assert len(payload["days"]) == day_count
        assert payload["days"][0] == _empty_grid_day_payload(f"{current_year}-01-01")
        assert payload["days"][-1] == _empty_grid_day_payload(f"{current_year}-12-31")
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_exploration_contract_split_returns_bootstrap_and_grid_separately() -> None:
    workspace_root = _create_workspace_dir(prefix="exploration-contract-split")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        _seed_split_contract_scenario(runtime=runtime)

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            bootstrap_response = client.get(
                "/api/exploration/bootstrap?start=2024-01-01&end=2024-01-03"
            )
            grid_response = client.get("/api/exploration?start=2024-01-01&end=2024-01-03")

        assert bootstrap_response.status_code == 200
        assert bootstrap_response.json() == {
            "range": {"start": "2024-01-01", "end": "2024-01-03"},
            "view_modes": [
                {
                    "id": "activity",
                    "label": "Activity",
                    "description": "Default heat intensity across all timeline sources.",
                },
                {
                    "id": "calendar",
                    "label": "Calendar",
                    "description": "Highlights days with calendar activity.",
                },
            ],
            "persons": [
                {"id": 1, "name": "Anna", "role": "Family"},
                {"id": 2, "name": "Milo", "role": "Travel buddy"},
            ],
            "tags": [
                {"path": "family/anna", "label": "Family Anna"},
                {"path": "mood/focused", "label": "Focused"},
                {"path": "projects/apollo", "label": "Project Apollo"},
            ],
        }

        assert grid_response.status_code == 200
        assert grid_response.json() == {
            "range": {"start": "2024-01-01", "end": "2024-01-03"},
            "days": [
                _empty_grid_day_payload("2024-01-01"),
                _active_grid_day_payload(
                    "2024-01-02",
                    count=2,
                    activity_score=40,
                    color_value="medium",
                ),
                _empty_grid_day_payload("2024-01-03"),
            ],
        }
        assert "days" not in bootstrap_response.json()
        assert sorted(grid_response.json()["days"][1]) == [
            "activity_score",
            "color_value",
            "count",
            "date",
            "has_data",
        ]
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_exploration_grid_endpoint_uses_derived_bounds_without_canonical_fallback() -> None:
    workspace_root = _create_workspace_dir(prefix="exploration-grid-bounds")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)

        with runtime.session_factory() as session:
            source = Source(name="Calendar", type="calendar", config={})
            session.add(source)
            session.flush()
            overall_view = _create_daily_view(session=session)
            session.add(
                Event(
                    source_id=source.id,
                    type="calendar",
                    timestamp_start=datetime(2024, 5, 10, 9, 0, tzinfo=UTC),
                    timestamp_end=None,
                    title="Canonical only",
                    summary=None,
                    latitude=None,
                    longitude=None,
                    raw_payload={},
                    derived_payload={},
                )
            )
            session.add(
                DailyAggregate(
                    date=date(2025, 2, 3),
                    daily_view_id=overall_view.id,
                    total_events=1,
                    media_count=0,
                    activity_score=5,
                )
            )
            session.commit()

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get("/api/exploration")

        assert response.status_code == 200
        payload = response.json()
        assert payload["range"] == {
            "start": "2025-01-01",
            "end": "2025-12-31",
        }
        assert payload["days"][0] == _empty_grid_day_payload("2025-01-01")
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_exploration_grid_endpoint_accepts_server_side_filter_parameters() -> None:
    workspace_root = _create_workspace_dir(prefix="exploration-grid-filters")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        _seed_filter_scenario(runtime=runtime)

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get(
                "/api/exploration?start=2024-01-01&end=2024-01-03"
                "&view_mode=photo"
                "&person_ids=1"
                "&tag_paths=travel"
            )

        assert response.status_code == 200
        assert response.json() == {
            "range": {"start": "2024-01-01", "end": "2024-01-03"},
            "days": [
                _empty_grid_day_payload("2024-01-01"),
                _active_grid_day_payload(
                    "2024-01-02",
                    count=1,
                    activity_score=80,
                    color_value="high",
                ),
                _empty_grid_day_payload("2024-01-03"),
            ],
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_exploration_grid_endpoint_selects_requested_daily_view_rows() -> None:
    workspace_root = _create_workspace_dir(prefix="exploration-grid-view-selection")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        _seed_split_contract_scenario(runtime=runtime)

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            activity_response = client.get(
                "/api/exploration?start=2024-01-02&end=2024-01-02&view_mode=activity"
            )
            calendar_response = client.get(
                "/api/exploration?start=2024-01-02&end=2024-01-02&view_mode=calendar"
            )

        assert activity_response.status_code == 200
        assert activity_response.json() == {
            "range": {"start": "2024-01-02", "end": "2024-01-02"},
            "days": [
                _active_grid_day_payload(
                    "2024-01-02",
                    count=2,
                    activity_score=40,
                    color_value="medium",
                )
            ],
        }

        assert calendar_response.status_code == 200
        assert calendar_response.json() == {
            "range": {"start": "2024-01-02", "end": "2024-01-02"},
            "days": [
                _active_grid_day_payload(
                    "2024-01-02",
                    count=1,
                    activity_score=20,
                    color_value="low",
                )
            ],
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_exploration_bootstrap_endpoint_orders_daily_views_deterministically() -> None:
    workspace_root = _create_workspace_dir(prefix="exploration-bootstrap-view-order")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)

        with runtime.session_factory() as session:
            _create_daily_view(
                session=session,
                aggregate_scope=DAILY_AGGREGATE_SCOPE_SOURCE_TYPE,
                source_type="video",
            )
            _create_daily_view(session=session)
            _create_daily_view(
                session=session,
                aggregate_scope=DAILY_AGGREGATE_SCOPE_SOURCE_TYPE,
                source_type="calendar",
            )
            session.commit()

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get("/api/exploration/bootstrap")

        assert response.status_code == 200
        assert response.json()["view_modes"] == [
            {
                "id": "activity",
                "label": "Activity",
                "description": "Default heat intensity across all timeline sources.",
            },
            {
                "id": "calendar",
                "label": "Calendar",
                "description": "Highlights days with calendar activity.",
            },
            {
                "id": "video",
                "label": "Video",
                "description": "Highlights days with video activity.",
            },
        ]
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_exploration_grid_endpoint_rejects_view_mode_missing_from_daily_view_catalog() -> None:
    workspace_root = _create_workspace_dir(prefix="exploration-grid-invalid-view")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)

        with runtime.session_factory() as session:
            _create_daily_view(session=session)
            session.commit()

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get("/api/exploration?view_mode=calendar")

        assert response.status_code == 400
        assert response.json() == {"detail": "unsupported view_mode: calendar"}
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_exploration_grid_filtered_out_days_return_zero_count_and_empty_state() -> None:
    workspace_root = _create_workspace_dir(prefix="exploration-grid-filtered-count")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        _seed_filter_scenario(runtime=runtime)

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get(
                "/api/exploration?start=2024-01-02&end=2024-01-03"
                "&view_mode=activity"
                "&person_ids=999"
            )

        assert response.status_code == 200
        assert response.json() == {
            "range": {"start": "2024-01-02", "end": "2024-01-03"},
            "days": [
                _empty_grid_day_payload("2024-01-02"),
                _empty_grid_day_payload("2024-01-03"),
            ],
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_exploration_grid_returns_empty_day_when_selected_view_has_no_row() -> None:
    workspace_root = _create_workspace_dir(prefix="exploration-grid-empty-selected-view")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        _seed_filter_scenario(runtime=runtime)

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get(
                "/api/exploration?start=2024-01-02&end=2024-01-03&view_mode=photo"
            )

        assert response.status_code == 200
        assert response.json() == {
            "range": {"start": "2024-01-02", "end": "2024-01-03"},
            "days": [
                _active_grid_day_payload(
                    "2024-01-02",
                    count=1,
                    activity_score=80,
                    color_value="high",
                ),
                _empty_grid_day_payload("2024-01-03"),
            ],
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_exploration_grid_uses_daily_view_metadata_thresholds_for_color_value() -> None:
    workspace_root = _create_workspace_dir(prefix="exploration-grid-view-thresholds")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)

        with runtime.session_factory() as session:
            custom_view = _create_daily_view(session=session)
            custom_view.metadata_json = {
                **build_default_daily_view_metadata(),
                "activity_score_color_thresholds": [
                    {"activity_score": 70, "color_value": "high"},
                    {"activity_score": 10, "color_value": "low"},
                    {"activity_score": 40, "color_value": "medium"},
                ],
            }
            session.add(
                DailyAggregate(
                    date=date(2024, 1, 2),
                    daily_view_id=custom_view.id,
                    total_events=1,
                    media_count=0,
                    activity_score=12,
                )
            )
            session.add(
                DailyAggregate(
                    date=date(2024, 1, 3),
                    daily_view_id=custom_view.id,
                    total_events=1,
                    media_count=0,
                    activity_score=5,
                )
            )
            session.commit()

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get(
                "/api/exploration?start=2024-01-02&end=2024-01-03&view_mode=activity"
            )

        assert response.status_code == 200
        assert response.json() == {
            "range": {"start": "2024-01-02", "end": "2024-01-03"},
            "days": [
                _active_grid_day_payload(
                    "2024-01-02",
                    count=1,
                    activity_score=12,
                    color_value="low",
                ),
                _active_grid_day_payload(
                    "2024-01-03",
                    count=1,
                    activity_score=5,
                    color_value="empty",
                ),
            ],
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_exploration_bootstrap_endpoint_rejects_partial_explicit_range() -> None:
    workspace_root = _create_workspace_dir(prefix="exploration-bootstrap-partial")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        app = create_app(settings=runtime.settings)

        with TestClient(app) as client:
            response = client.get("/api/exploration/bootstrap?start=2024-01-01")

        assert response.status_code == 400
        assert response.json() == {
            "detail": "start and end must both be provided together",
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_exploration_grid_endpoint_rejects_partial_explicit_range() -> None:
    workspace_root = _create_workspace_dir(prefix="exploration-grid-partial")
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


def test_day_context_endpoint_remains_separate_from_grid_activity_loading() -> None:
    workspace_root = _create_workspace_dir(prefix="exploration-day-context-separate")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)

        with runtime.session_factory() as session:
            source = Source(name="Calendar", type="calendar", config={})
            anna = Person(name="Anna", aliases=None, metadata_json={"role": "Family"})
            travel_tag = Tag(label="Travel", path="travel/europe", metadata_json=None)
            session.add_all([source, anna, travel_tag])
            session.flush()
            overall_view = _create_daily_view(session=session)

            event = Event(
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
            asset = Asset(
                external_id="asset-1",
                media_type="photo",
                timestamp=datetime(2024, 1, 2, 10, 30, tzinfo=UTC),
                latitude=48.8566,
                longitude=2.3522,
                metadata_json={"label": "Museum"},
            )
            session.add_all([event, asset])
            session.flush()

            session.add_all(
                [
                    EventPerson(event_id=event.id, person_id=anna.id),
                    AssetPerson(asset_id=asset.id, person_id=anna.id),
                    EventTag(event_id=event.id, tag_id=travel_tag.id),
                    AssetTag(asset_id=asset.id, tag_id=travel_tag.id),
                    DailyAggregate(
                        date=date(2024, 1, 2),
                        daily_view_id=overall_view.id,
                        total_events=1,
                        media_count=1,
                        activity_score=20,
                        tag_summary_json=[
                            {
                                "path": "travel/europe",
                                "label": "Travel",
                                "count": 2,
                            }
                        ],
                        person_summary_json=[
                            {
                                "person_id": anna.id,
                                "name": "Anna",
                                "role": "Family",
                                "count": 2,
                            }
                        ],
                        location_summary_json=[],
                    ),
                ]
            )
            session.commit()

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            grid_response = client.get("/api/exploration?start=2024-01-01&end=2024-01-02")
            context_response = client.get(
                "/api/days/context?start=2024-01-01&end=2024-01-02"
            )

        assert grid_response.status_code == 200
        assert context_response.status_code == 200
        assert sorted(grid_response.json()["days"][1]) == [
            "activity_score",
            "color_value",
            "count",
            "date",
            "has_data",
        ]
        assert context_response.json()["days"][1] == {
            "date": "2024-01-02",
            "persons": [{"id": 1, "name": "Anna", "role": "Family"}],
            "tags": [{"path": "travel/europe", "label": "Travel"}],
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
            ],
            "summary_counts": {"events": 1, "assets": 1, "places": 2},
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def _seed_split_contract_scenario(*, runtime) -> None:
    with runtime.session_factory() as session:
        source = Source(name="Calendar", type="calendar", config={})
        anna = Person(name="Anna", aliases=None, metadata_json={"role": "Family"})
        milo = Person(name="Milo", aliases=None, metadata_json={"role": "Travel buddy"})
        project_tag = Tag(label="Project Apollo", path="projects/apollo", metadata_json=None)
        family_tag = Tag(label="Family Anna", path="family/anna", metadata_json=None)
        mood_tag = Tag(label="Focused", path="mood/focused", metadata_json=None)
        session.add_all([source, anna, milo, project_tag, family_tag, mood_tag])
        session.flush()
        overall_view = _create_daily_view(session=session)
        calendar_view = _create_daily_view(
            session=session,
            aggregate_scope=DAILY_AGGREGATE_SCOPE_SOURCE_TYPE,
            source_type="calendar",
        )

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
                    daily_view_id=overall_view.id,
                    total_events=1,
                    media_count=1,
                    activity_score=40,
                    tag_summary_json=[
                        {"path": "family/anna", "label": "Family Anna", "count": 1},
                        {"path": "projects/apollo", "label": "Project Apollo", "count": 1},
                    ],
                    person_summary_json=[
                        {"person_id": anna.id, "name": "Anna", "role": "Family", "count": 1},
                        {"person_id": milo.id, "name": "Milo", "role": "Travel buddy", "count": 1},
                    ],
                    location_summary_json=[],
                ),
                DailyAggregate(
                    date=date(2024, 1, 2),
                    daily_view_id=calendar_view.id,
                    total_events=1,
                    media_count=0,
                    activity_score=20,
                ),
            ]
        )
        session.commit()


def _seed_filter_scenario(*, runtime) -> None:
    with runtime.session_factory() as session:
        source = Source(name="Calendar", type="calendar", config={})
        anna = Person(name="Anna", aliases=None, metadata_json={"role": "Family"})
        ben = Person(name="Ben", aliases=None, metadata_json={"role": "Friend"})
        travel_tag = Tag(label="Europe", path="travel/europe", metadata_json=None)
        family_tag = Tag(label="Family", path="people/family", metadata_json=None)
        session.add_all([source, anna, ben, travel_tag, family_tag])
        session.flush()
        overall_view = _create_daily_view(session=session)
        photo_view = _create_daily_view(
            session=session,
            aggregate_scope=DAILY_AGGREGATE_SCOPE_SOURCE_TYPE,
            source_type="photo",
        )

        first_event = Event(
            source_id=source.id,
            type="calendar",
            timestamp_start=datetime(2024, 1, 2, 9, 0, tzinfo=UTC),
            timestamp_end=None,
            title="Berlin trip",
            summary=None,
            latitude=None,
            longitude=None,
            raw_payload={},
            derived_payload={},
        )
        second_event = Event(
            source_id=source.id,
            type="calendar",
            timestamp_start=datetime(2024, 1, 3, 9, 0, tzinfo=UTC),
            timestamp_end=None,
            title="Family breakfast",
            summary=None,
            latitude=None,
            longitude=None,
            raw_payload={},
            derived_payload={},
        )
        session.add_all([first_event, second_event])
        session.flush()
        session.add_all(
            [
                EventPerson(event_id=first_event.id, person_id=anna.id),
                EventPerson(event_id=second_event.id, person_id=ben.id),
                EventTag(event_id=first_event.id, tag_id=travel_tag.id),
                EventTag(event_id=second_event.id, tag_id=family_tag.id),
                DailyAggregate(
                    date=date(2024, 1, 2),
                    daily_view_id=overall_view.id,
                    total_events=1,
                    media_count=0,
                    activity_score=12,
                    tag_summary_json=[
                        {"path": "travel/europe", "label": "Europe", "count": 1}
                    ],
                    person_summary_json=[
                        {"person_id": anna.id, "name": "Anna", "role": "Family", "count": 1}
                    ],
                    location_summary_json=[],
                ),
                DailyAggregate(
                    date=date(2024, 1, 3),
                    daily_view_id=overall_view.id,
                    total_events=1,
                    media_count=0,
                    activity_score=30,
                    tag_summary_json=[
                        {"path": "people/family", "label": "Family", "count": 1}
                    ],
                    person_summary_json=[
                        {"person_id": ben.id, "name": "Ben", "role": "Friend", "count": 1}
                    ],
                    location_summary_json=[],
                ),
                DailyAggregate(
                    date=date(2024, 1, 2),
                    daily_view_id=photo_view.id,
                    total_events=0,
                    media_count=1,
                    activity_score=80,
                    tag_summary_json=[
                        {"path": "travel/europe", "label": "Europe", "count": 1}
                    ],
                    person_summary_json=[
                        {"person_id": anna.id, "name": "Anna", "role": "Family", "count": 1}
                    ],
                    location_summary_json=[],
                ),
            ]
        )
        session.commit()


def _fallback_view_modes_payload() -> list[dict[str, str]]:
    return [
        {
            "id": "activity",
            "label": "Activity",
            "description": "Default heat intensity across all timeline sources.",
        },
        {
            "id": "photos",
            "label": "Photos",
            "description": "Highlights days with photos activity.",
        },
        {
            "id": "videos",
            "label": "Videos",
            "description": "Highlights days with videos activity.",
        },
        {
            "id": "music",
            "label": "Music",
            "description": "Highlights days with music activity.",
        },
        {
            "id": "calendar",
            "label": "Calendar",
            "description": "Highlights days with calendar activity.",
        },
        {
            "id": "sports",
            "label": "Sports",
            "description": "Highlights days with sports activity.",
        },
    ]


def _empty_grid_day_payload(day: str) -> dict[str, object]:
    return {
        "date": day,
        "count": 0,
        "activity_score": 0,
        "color_value": "empty",
        "has_data": False,
    }


def _active_grid_day_payload(
    day: str,
    *,
    count: int,
    activity_score: int,
    color_value: str,
) -> dict[str, object]:
    return {
        "date": day,
        "count": count,
        "activity_score": activity_score,
        "color_value": color_value,
        "has_data": True,
    }


def _create_runtime(*, workspace_root: Path):
    database_path = workspace_root / "pixelpast.db"
    settings = Settings(database_url=f"sqlite:///{database_path.as_posix()}")
    runtime = create_runtime_context(settings=settings)
    initialize_database(runtime)
    return runtime


def _create_daily_view(
    *,
    session,
    aggregate_scope: str = "overall",
    source_type: str | None = None,
) -> DailyView:
    if aggregate_scope == "overall":
        daily_view = DailyView(
            aggregate_scope=aggregate_scope,
            source_type=None,
            label="Activity",
            description="Default heat intensity across all timeline sources.",
            metadata_json=build_default_daily_view_metadata(),
        )
    else:
        assert source_type is not None
        normalized_source_type = source_type.replace("_", " ")
        daily_view = DailyView(
            aggregate_scope=aggregate_scope,
            source_type=source_type,
            label=normalized_source_type.title(),
            description=f"Highlights days with {normalized_source_type} activity.",
            metadata_json=build_default_daily_view_metadata(),
        )

    session.add(daily_view)
    session.flush()
    return daily_view


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
