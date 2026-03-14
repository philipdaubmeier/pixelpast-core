"""Daily aggregate job tests."""

from __future__ import annotations

import shutil
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from pixelpast.analytics.daily_aggregate import DailyAggregateJob
from pixelpast.persistence.models import (
    Asset,
    DAILY_AGGREGATE_SCOPE_SOURCE_TYPE,
    DailyAggregate,
    Event,
    Source,
)
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import Settings


def test_daily_aggregate_job_clears_rows_for_empty_canonical_dataset() -> None:
    workspace_root = _create_workspace_dir(prefix="daily-aggregate-empty")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)

        with runtime.session_factory() as session:
            session.add(
                DailyAggregate(
                    date=date(2024, 1, 1),
                    total_events=9,
                    media_count=4,
                    activity_score=13,
                    metadata_json={"score_version": "stale"},
                )
            )
            session.commit()

        result = DailyAggregateJob().run(runtime=runtime)

        assert result.mode == "full"
        assert result.aggregate_count == 0
        assert result.total_events == 0
        assert result.media_count == 0

        with runtime.session_factory() as session:
            aggregates = list(session.execute(select(DailyAggregate)).scalars())

        assert aggregates == []
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_daily_aggregate_job_recomputes_range_idempotently() -> None:
    workspace_root = _create_workspace_dir(prefix="daily-aggregate-range")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        _seed_timeline(
            runtime=runtime,
            events=[
                datetime(2024, 1, 1, 8, 0, tzinfo=UTC),
                datetime(2024, 1, 2, 9, 0, tzinfo=UTC),
            ],
            assets=[
                datetime(2024, 1, 2, 10, 0, tzinfo=UTC),
                datetime(2024, 1, 3, 11, 0, tzinfo=UTC),
            ],
        )

        initial_result = DailyAggregateJob().run(runtime=runtime)
        assert initial_result.aggregate_count == 3

        with runtime.session_factory() as session:
            source = session.execute(select(Source)).scalar_one()
            session.add(
                Event(
                    source_id=source.id,
                    type="calendar",
                    timestamp_start=datetime(2024, 1, 2, 18, 30, tzinfo=UTC),
                    timestamp_end=None,
                    title="Late update",
                    summary=None,
                    latitude=None,
                    longitude=None,
                    raw_payload={},
                    derived_payload={},
                )
            )
            session.commit()

        range_result = DailyAggregateJob().run(
            runtime=runtime,
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 2),
        )
        repeated_result = DailyAggregateJob().run(
            runtime=runtime,
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 2),
        )

        assert range_result.mode == "range"
        assert range_result.aggregate_count == 1
        assert range_result.total_events == 2
        assert range_result.media_count == 1
        assert repeated_result.aggregate_count == 1

        with runtime.session_factory() as session:
            aggregates = list(
                session.execute(
                    select(DailyAggregate).order_by(DailyAggregate.date)
                ).scalars()
            )

        assert [
            (
                aggregate.date.isoformat(),
                aggregate.total_events,
                aggregate.media_count,
                aggregate.activity_score,
                aggregate.metadata_json["score_formula"],
            )
            for aggregate in aggregates
        ] == [
            (
                "2024-01-01",
                1,
                0,
                1,
                "activity_score = total_events + media_count",
            ),
            (
                "2024-01-02",
                2,
                1,
                3,
                "activity_score = total_events + media_count",
            ),
            (
                "2024-01-03",
                0,
                1,
                1,
                "activity_score = total_events + media_count",
            ),
        ]
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_daily_aggregate_schema_allows_multiple_scopes_for_same_day() -> None:
    workspace_root = _create_workspace_dir(prefix="daily-aggregate-scopes")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)

        with runtime.session_factory() as session:
            session.add_all(
                [
                    DailyAggregate(
                        date=date(2024, 1, 2),
                        total_events=2,
                        media_count=1,
                        activity_score=3,
                        metadata_json={"score_version": "v2"},
                    ),
                    DailyAggregate(
                        date=date(2024, 1, 2),
                        aggregate_scope=DAILY_AGGREGATE_SCOPE_SOURCE_TYPE,
                        source_type="photo",
                        total_events=0,
                        media_count=1,
                        activity_score=1,
                        tag_summary_json=[
                            {
                                "path": "travel/city",
                                "label": "City",
                                "count": 1,
                            }
                        ],
                        person_summary_json=[
                            {
                                "person_id": 1,
                                "name": "Anna",
                                "count": 1,
                            }
                        ],
                        location_summary_json=[
                            {
                                "label": "Berlin",
                                "latitude": 52.52,
                                "longitude": 13.405,
                                "count": 1,
                            }
                        ],
                        metadata_json={"score_version": "v2"},
                    ),
                ]
            )
            session.commit()

        with runtime.session_factory() as session:
            aggregates = list(
                session.execute(
                    select(DailyAggregate).order_by(
                        DailyAggregate.date,
                        DailyAggregate.aggregate_scope,
                        DailyAggregate.source_type,
                    )
                ).scalars()
            )

        assert len(aggregates) == 2
        assert aggregates[0].aggregate_scope == "overall"
        assert aggregates[0].source_type == "__all__"
        assert aggregates[0].tag_summary_json == []
        assert aggregates[1].aggregate_scope == DAILY_AGGREGATE_SCOPE_SOURCE_TYPE
        assert aggregates[1].source_type == "photo"
        assert aggregates[1].tag_summary_json == [
            {"path": "travel/city", "label": "City", "count": 1}
        ]
        assert aggregates[1].person_summary_json == [
            {"person_id": 1, "name": "Anna", "count": 1}
        ]
        assert aggregates[1].location_summary_json == [
            {
                "label": "Berlin",
                "latitude": 52.52,
                "longitude": 13.405,
                "count": 1,
            }
        ]
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
