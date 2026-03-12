"""Integration tests for heatmap and day-detail API endpoints."""

from __future__ import annotations

import shutil
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from pixelpast.api.app import create_app
from pixelpast.persistence.models import Asset, DailyAggregate, Event, Source
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import Settings


def test_heatmap_endpoint_returns_empty_range() -> None:
    workspace_root = _create_workspace_dir(prefix="timeline-api-heatmap-empty")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        app = create_app(settings=runtime.settings)

        with TestClient(app) as client:
            response = client.get("/heatmap?start=2024-01-01&end=2024-01-03")

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
            response = client.get("/heatmap?start=2024-01-02&end=2024-01-04")

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
            response = client.get("/days/2024-01-02")

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
            response = client.get("/days/2024-01-02")

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
            response = client.get("/days/2024-01-02")

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


def _create_workspace_dir(*, prefix: str) -> Path:
    workspace_root = Path("var") / f"{prefix}-{uuid4().hex}"
    workspace_root.mkdir(parents=True, exist_ok=False)
    return workspace_root
