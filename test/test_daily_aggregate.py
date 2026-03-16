"""Daily aggregate job tests."""

from __future__ import annotations

import shutil
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from pixelpast.analytics.daily_aggregate import (
    DailyAggregateCanonicalInputs,
    DailyAggregateJob,
    build_daily_aggregate_snapshots,
)
from pixelpast.analytics.daily_views import build_daily_view
from pixelpast.persistence.models import (
    DAILY_AGGREGATE_OVERALL_SOURCE_TYPE,
    DAILY_AGGREGATE_SCOPE_SOURCE_TYPE,
    Asset,
    AssetPerson,
    AssetTag,
    DailyAggregate,
    DailyView,
    Event,
    EventPerson,
    EventTag,
    JobRun,
    Person,
    Source,
    Tag,
)
from pixelpast.shared.progress import JobProgressSnapshot
from pixelpast.persistence.repositories.daily_aggregates import (
    CanonicalAssetAggregateInput,
    CanonicalEventAggregateInput,
    CanonicalPersonAggregateInput,
    CanonicalTagAggregateInput,
)
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import Settings


def test_build_daily_aggregate_snapshots_is_deterministic_without_database() -> None:
    base_inputs = DailyAggregateCanonicalInputs(
        event_inputs=[
            CanonicalEventAggregateInput(
                day=date(2024, 1, 2),
                source_type="calendar",
                event_type="calendar",
                title="Planning",
                latitude=52.52,
                longitude=13.405,
            )
        ],
        asset_inputs=[
            CanonicalAssetAggregateInput(
                day=date(2024, 1, 2),
                source_type="photo",
                external_id="photos/trip/day-2.jpg",
                media_type="photo",
                summary=None,
                metadata_json={"title": "Museum"},
                latitude=48.8566,
                longitude=2.3522,
            ),
            CanonicalAssetAggregateInput(
                day=date(2024, 1, 2),
                source_type="photo",
                external_id="photos/trip/day-2-b.jpg",
                media_type="photo",
                summary="Museum",
                metadata_json={},
                latitude=48.8566,
                longitude=2.3522,
            ),
        ],
        tag_inputs=[
            CanonicalTagAggregateInput(
                day=date(2024, 1, 2),
                source_type="photo",
                path="travel",
                label="Travel",
            ),
            CanonicalTagAggregateInput(
                day=date(2024, 1, 2),
                source_type="calendar",
                path="projects/apollo",
                label="Project Apollo",
            ),
        ],
        person_inputs=[
            CanonicalPersonAggregateInput(
                day=date(2024, 1, 2),
                source_type="photo",
                person_id=2,
                name="Ben",
                role="Friend",
            ),
            CanonicalPersonAggregateInput(
                day=date(2024, 1, 2),
                source_type="calendar",
                person_id=1,
                name="Anna",
                role="Family",
            ),
        ],
    )
    reordered_inputs = DailyAggregateCanonicalInputs(
        event_inputs=list(reversed(base_inputs.event_inputs)),
        asset_inputs=list(reversed(base_inputs.asset_inputs)),
        tag_inputs=list(reversed(base_inputs.tag_inputs)),
        person_inputs=list(reversed(base_inputs.person_inputs)),
    )

    first_pass = [
        _serialize_snapshot(snapshot)
        for snapshot in build_daily_aggregate_snapshots(base_inputs)
    ]
    second_pass = [
        _serialize_snapshot(snapshot)
        for snapshot in build_daily_aggregate_snapshots(reordered_inputs)
    ]

    assert first_pass == second_pass
    assert first_pass == [
        {
            "date": "2024-01-02",
            "scope": "overall",
            "source_type": "__all__",
            "total_events": 1,
            "media_count": 2,
            "activity_score": 3,
            "tag_summary": [
                {"path": "projects/apollo", "label": "Project Apollo", "count": 1},
                {"path": "travel", "label": "Travel", "count": 1},
            ],
            "person_summary": [
                {"person_id": 1, "name": "Anna", "role": "Family", "count": 1},
                {"person_id": 2, "name": "Ben", "role": "Friend", "count": 1},
            ],
            "location_summary": [
                {
                    "label": "Museum",
                    "latitude": 48.8566,
                    "longitude": 2.3522,
                    "count": 2,
                },
                {
                    "label": "Planning",
                    "latitude": 52.52,
                    "longitude": 13.405,
                    "count": 1,
                },
            ],
            "score_version": "v2",
        },
        {
            "date": "2024-01-02",
            "scope": "source_type",
            "source_type": "calendar",
            "total_events": 1,
            "media_count": 0,
            "activity_score": 1,
            "tag_summary": [
                {"path": "projects/apollo", "label": "Project Apollo", "count": 1}
            ],
            "person_summary": [
                {"person_id": 1, "name": "Anna", "role": "Family", "count": 1}
            ],
            "location_summary": [
                {
                    "label": "Planning",
                    "latitude": 52.52,
                    "longitude": 13.405,
                    "count": 1,
                }
            ],
            "score_version": "v2",
        },
        {
            "date": "2024-01-02",
            "scope": "source_type",
            "source_type": "photo",
            "total_events": 0,
            "media_count": 2,
            "activity_score": 2,
            "tag_summary": [
                {"path": "travel", "label": "Travel", "count": 1}
            ],
            "person_summary": [
                {"person_id": 2, "name": "Ben", "role": "Friend", "count": 1}
            ],
            "location_summary": [
                {
                    "label": "Museum",
                    "latitude": 48.8566,
                    "longitude": 2.3522,
                    "count": 2,
                }
            ],
            "score_version": "v2",
        },
    ]


def test_build_daily_view_returns_stable_metadata() -> None:
    overall_view = build_daily_view(aggregate_scope="overall", source_type="__all__")
    photo_view = build_daily_view(
        aggregate_scope="source_type",
        source_type="photo",
    )

    assert overall_view.source_type is None
    assert overall_view.label == "Activity"
    assert overall_view.description == (
        "Default heat intensity across all timeline sources."
    )
    assert overall_view.metadata_json["score_version"] == "v2"
    assert photo_view.source_type == "photo"
    assert photo_view.label == "Photo"
    assert photo_view.description == "Highlights days with photo activity."
    assert photo_view.metadata_json["score_version"] == "v2"


def test_daily_aggregate_job_clears_rows_for_empty_canonical_dataset() -> None:
    workspace_root = _create_workspace_dir(prefix="daily-aggregate-empty")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)

        with runtime.session_factory() as session:
            overall_view = DailyView(
                aggregate_scope="overall",
                source_type=None,
                label="Activity",
                description="Default heat intensity across all timeline sources.",
                metadata_json={"score_version": "stale"},
            )
            session.add(overall_view)
            session.flush()
            session.add(
                DailyAggregate(
                    date=date(2024, 1, 1),
                    daily_view_id=overall_view.id,
                    total_events=9,
                    media_count=4,
                    activity_score=13,
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


def test_daily_aggregate_job_builds_connector_scoped_rows_with_semantic_summaries(
) -> None:
    workspace_root = _create_workspace_dir(prefix="daily-aggregate-v2")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)

        with runtime.session_factory() as session:
            calendar_source = Source(name="Calendar", type="calendar", config={})
            session.add(calendar_source)

            anna = Person(name="Anna", aliases=None, metadata_json={"role": "Family"})
            ben = Person(name="Ben", aliases=None, metadata_json={"role": "Friend"})
            milo = Person(name="Milo", aliases=None, metadata_json=None)
            project_tag = Tag(
                label="Project Apollo",
                path="projects/apollo",
                metadata_json=None,
            )
            travel_tag = Tag(label="Travel", path="travel", metadata_json=None)
            session.add_all([anna, ben, milo, project_tag, travel_tag])
            session.flush()

            mixed_event = Event(
                source_id=calendar_source.id,
                type="calendar",
                timestamp_start=datetime(2024, 1, 2, 10, 0, tzinfo=UTC),
                timestamp_end=None,
                title="Planning",
                summary=None,
                latitude=52.52,
                longitude=13.405,
                raw_payload={},
                derived_payload={},
            )
            tag_only_event = Event(
                source_id=calendar_source.id,
                type="calendar",
                timestamp_start=datetime(2024, 1, 3, 8, 0, tzinfo=UTC),
                timestamp_end=None,
                title="Trip prep",
                summary=None,
                latitude=None,
                longitude=None,
                raw_payload={},
                derived_payload={},
            )
            mixed_photo_one = Asset(
                external_id="asset-1",
                media_type="photo",
                timestamp=datetime(2024, 1, 2, 12, 0, tzinfo=UTC),
                summary=None,
                latitude=48.8566,
                longitude=2.3522,
                metadata_json={"title": "Museum"},
            )
            mixed_photo_two = Asset(
                external_id="asset-2",
                media_type="photo",
                timestamp=datetime(2024, 1, 2, 13, 0, tzinfo=UTC),
                summary="Museum",
                latitude=48.8566,
                longitude=2.3522,
                metadata_json={},
            )
            person_only_photo = Asset(
                external_id="asset-day-four",
                media_type="photo",
                timestamp=datetime(2024, 1, 4, 9, 30, tzinfo=UTC),
                summary=None,
                latitude=40.7128,
                longitude=-74.006,
                metadata_json={"filename": "asset-day-four.jpg"},
            )
            session.add_all(
                [
                    mixed_event,
                    tag_only_event,
                    mixed_photo_one,
                    mixed_photo_two,
                    person_only_photo,
                ]
            )
            session.flush()

            session.add_all(
                [
                    EventPerson(event_id=mixed_event.id, person_id=anna.id),
                    AssetPerson(asset_id=mixed_photo_one.id, person_id=ben.id),
                    AssetPerson(asset_id=mixed_photo_two.id, person_id=anna.id),
                    AssetPerson(asset_id=person_only_photo.id, person_id=milo.id),
                    EventTag(event_id=mixed_event.id, tag_id=project_tag.id),
                    EventTag(event_id=tag_only_event.id, tag_id=travel_tag.id),
                    AssetTag(asset_id=mixed_photo_one.id, tag_id=travel_tag.id),
                    AssetTag(asset_id=mixed_photo_two.id, tag_id=project_tag.id),
                ]
            )
            session.commit()

        result = DailyAggregateJob().run(runtime=runtime)

        assert result.mode == "full"
        assert result.aggregate_count == 7
        assert result.total_events == 2
        assert result.media_count == 3
        assert result.start_date == date(2024, 1, 2)
        assert result.end_date == date(2024, 1, 4)

        with runtime.session_factory() as session:
            stored_aggregates = list(
                session.execute(
                    select(DailyAggregate)
                    .join(DailyView, DailyView.id == DailyAggregate.daily_view_id)
                    .order_by(
                        DailyAggregate.date,
                        DailyView.aggregate_scope,
                        DailyView.source_type,
                    )
                ).scalars()
            )
            stored_views = list(
                session.execute(
                    select(DailyView).order_by(
                        DailyView.aggregate_scope,
                        DailyView.source_type,
                        DailyView.id,
                    )
                ).scalars()
            )

        aggregates = {
            (
                aggregate.date.isoformat(),
                aggregate.aggregate_scope,
                aggregate.source_type,
            ): aggregate
            for aggregate in stored_aggregates
        }

        mixed_overall = aggregates[("2024-01-02", "overall", "__all__")]
        assert mixed_overall.total_events == 1
        assert mixed_overall.media_count == 2
        assert mixed_overall.activity_score == 3
        assert mixed_overall.tag_summary_json == [
            {"path": "projects/apollo", "label": "Project Apollo", "count": 2},
            {"path": "travel", "label": "Travel", "count": 1},
        ]
        assert mixed_overall.person_summary_json == [
            {"person_id": 1, "name": "Anna", "role": "Family", "count": 2},
            {"person_id": 2, "name": "Ben", "role": "Friend", "count": 1},
        ]
        assert mixed_overall.location_summary_json == [
            {
                "label": "Museum",
                "latitude": 48.8566,
                "longitude": 2.3522,
                "count": 2,
            },
            {
                "label": "Planning",
                "latitude": 52.52,
                "longitude": 13.405,
                "count": 1,
            },
        ]
        assert mixed_overall.daily_view.metadata_json == {
            "score_version": "v2",
            "score_formula": "activity_score = total_events + media_count",
            "summary_version": "v1",
            "source_partitioning": "events use source.type; assets use media_type",
        }

        mixed_calendar = aggregates[("2024-01-02", "source_type", "calendar")]
        assert mixed_calendar.total_events == 1
        assert mixed_calendar.media_count == 0
        assert mixed_calendar.tag_summary_json == [
            {"path": "projects/apollo", "label": "Project Apollo", "count": 1}
        ]
        assert mixed_calendar.person_summary_json == [
            {"person_id": 1, "name": "Anna", "role": "Family", "count": 1}
        ]
        assert mixed_calendar.location_summary_json == [
            {
                "label": "Planning",
                "latitude": 52.52,
                "longitude": 13.405,
                "count": 1,
            }
        ]

        mixed_photo = aggregates[("2024-01-02", "source_type", "photo")]
        assert mixed_photo.total_events == 0
        assert mixed_photo.media_count == 2
        assert mixed_photo.tag_summary_json == [
            {"path": "projects/apollo", "label": "Project Apollo", "count": 1},
            {"path": "travel", "label": "Travel", "count": 1},
        ]
        assert mixed_photo.person_summary_json == [
            {"person_id": 1, "name": "Anna", "role": "Family", "count": 1},
            {"person_id": 2, "name": "Ben", "role": "Friend", "count": 1},
        ]
        assert mixed_photo.location_summary_json == [
            {
                "label": "Museum",
                "latitude": 48.8566,
                "longitude": 2.3522,
                "count": 2,
            }
        ]

        event_only_overall = aggregates[("2024-01-03", "overall", "__all__")]
        assert event_only_overall.total_events == 1
        assert event_only_overall.media_count == 0
        assert event_only_overall.tag_summary_json == [
            {"path": "travel", "label": "Travel", "count": 1}
        ]
        assert event_only_overall.person_summary_json == []
        assert event_only_overall.location_summary_json == []

        event_only_calendar = aggregates[("2024-01-03", "source_type", "calendar")]
        assert event_only_calendar.total_events == 1
        assert event_only_calendar.media_count == 0
        assert event_only_calendar.tag_summary_json == [
            {"path": "travel", "label": "Travel", "count": 1}
        ]
        assert event_only_calendar.person_summary_json == []

        asset_only_overall = aggregates[("2024-01-04", "overall", "__all__")]
        assert asset_only_overall.total_events == 0
        assert asset_only_overall.media_count == 1
        assert asset_only_overall.tag_summary_json == []
        assert asset_only_overall.person_summary_json == [
            {"person_id": 3, "name": "Milo", "role": None, "count": 1}
        ]
        assert asset_only_overall.location_summary_json == [
            {
                "label": "asset-day-four.jpg",
                "latitude": 40.7128,
                "longitude": -74.006,
                "count": 1,
            }
        ]

        asset_only_photo = aggregates[("2024-01-04", "source_type", "photo")]
        assert asset_only_photo.total_events == 0
        assert asset_only_photo.media_count == 1
        assert asset_only_photo.tag_summary_json == []
        assert asset_only_photo.person_summary_json == [
            {"person_id": 3, "name": "Milo", "role": None, "count": 1}
        ]

        assert all(
            aggregate.source_type == DAILY_AGGREGATE_OVERALL_SOURCE_TYPE
            or aggregate.aggregate_scope == DAILY_AGGREGATE_SCOPE_SOURCE_TYPE
            for aggregate in stored_aggregates
        )
        assert [
            (
                daily_view.aggregate_scope,
                daily_view.source_type,
                daily_view.label,
                daily_view.metadata_json["score_version"],
            )
            for daily_view in stored_views
        ] == [
            ("overall", None, "Activity", "v2"),
            ("source_type", "calendar", "Calendar", "v2"),
            ("source_type", "photo", "Photo", "v2"),
        ]
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_daily_aggregate_job_recomputes_range_idempotently_for_v2_rows() -> None:
    workspace_root = _create_workspace_dir(prefix="daily-aggregate-range")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)

        with runtime.session_factory() as session:
            calendar_source = Source(name="Calendar", type="calendar", config={})
            session.add(calendar_source)
            session.flush()

            session.add_all(
                [
                    Event(
                        source_id=calendar_source.id,
                        type="calendar",
                        timestamp_start=datetime(2024, 1, 1, 8, 0, tzinfo=UTC),
                        timestamp_end=None,
                        title="Day one",
                        summary=None,
                        latitude=None,
                        longitude=None,
                        raw_payload={},
                        derived_payload={},
                    ),
                    Event(
                        source_id=calendar_source.id,
                        type="calendar",
                        timestamp_start=datetime(2024, 1, 2, 9, 0, tzinfo=UTC),
                        timestamp_end=None,
                        title="Day two",
                        summary=None,
                        latitude=None,
                        longitude=None,
                        raw_payload={},
                        derived_payload={},
                    ),
                    Asset(
                        external_id="asset-1",
                        media_type="photo",
                        timestamp=datetime(2024, 1, 2, 10, 0, tzinfo=UTC),
                        summary=None,
                        latitude=None,
                        longitude=None,
                        metadata_json={},
                    ),
                    Asset(
                        external_id="asset-2",
                        media_type="photo",
                        timestamp=datetime(2024, 1, 3, 11, 0, tzinfo=UTC),
                        summary=None,
                        latitude=None,
                        longitude=None,
                        metadata_json={},
                    ),
                ]
            )
            session.commit()

        initial_result = DailyAggregateJob().run(runtime=runtime)
        assert initial_result.aggregate_count == 7

        with runtime.session_factory() as session:
            initial_view_ids = {
                (
                    daily_view.aggregate_scope,
                    daily_view.source_type,
                ): daily_view.id
                for daily_view in session.execute(
                    select(DailyView).order_by(
                        DailyView.aggregate_scope,
                        DailyView.source_type,
                        DailyView.id,
                    )
                ).scalars()
            }

        with runtime.session_factory() as session:
            calendar_source = session.execute(select(Source)).scalar_one()
            session.add(
                Event(
                    source_id=calendar_source.id,
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
        with runtime.session_factory() as session:
            first_pass_rows = [
                _serialize_aggregate(aggregate)
                for aggregate in session.execute(
                    select(DailyAggregate)
                    .join(DailyView, DailyView.id == DailyAggregate.daily_view_id)
                    .order_by(
                        DailyAggregate.date,
                        DailyView.aggregate_scope,
                        DailyView.source_type,
                    )
                ).scalars()
            ]

        repeated_result = DailyAggregateJob().run(
            runtime=runtime,
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 2),
        )
        with runtime.session_factory() as session:
            second_pass_rows = [
                _serialize_aggregate(aggregate)
                for aggregate in session.execute(
                    select(DailyAggregate)
                    .join(DailyView, DailyView.id == DailyAggregate.daily_view_id)
                    .order_by(
                        DailyAggregate.date,
                        DailyView.aggregate_scope,
                        DailyView.source_type,
                    )
                ).scalars()
            ]
            repeated_view_ids = {
                (
                    daily_view.aggregate_scope,
                    daily_view.source_type,
                ): daily_view.id
                for daily_view in session.execute(
                    select(DailyView).order_by(
                        DailyView.aggregate_scope,
                        DailyView.source_type,
                        DailyView.id,
                    )
                ).scalars()
            }

        assert range_result.mode == "range"
        assert range_result.aggregate_count == 3
        assert range_result.total_events == 2
        assert range_result.media_count == 1
        assert repeated_result.aggregate_count == 3
        assert repeated_view_ids == initial_view_ids
        assert first_pass_rows == second_pass_rows
        assert first_pass_rows == [
            {
                "date": "2024-01-01",
                "scope": "overall",
                "source_type": "__all__",
                "total_events": 1,
                "media_count": 0,
                "activity_score": 1,
                "tag_summary": [],
                "person_summary": [],
                "location_summary": [],
                "score_version": "v2",
            },
            {
                "date": "2024-01-01",
                "scope": "source_type",
                "source_type": "calendar",
                "total_events": 1,
                "media_count": 0,
                "activity_score": 1,
                "tag_summary": [],
                "person_summary": [],
                "location_summary": [],
                "score_version": "v2",
            },
            {
                "date": "2024-01-02",
                "scope": "overall",
                "source_type": "__all__",
                "total_events": 2,
                "media_count": 1,
                "activity_score": 3,
                "tag_summary": [],
                "person_summary": [],
                "location_summary": [],
                "score_version": "v2",
            },
            {
                "date": "2024-01-02",
                "scope": "source_type",
                "source_type": "calendar",
                "total_events": 2,
                "media_count": 0,
                "activity_score": 2,
                "tag_summary": [],
                "person_summary": [],
                "location_summary": [],
                "score_version": "v2",
            },
            {
                "date": "2024-01-02",
                "scope": "source_type",
                "source_type": "photo",
                "total_events": 0,
                "media_count": 1,
                "activity_score": 1,
                "tag_summary": [],
                "person_summary": [],
                "location_summary": [],
                "score_version": "v2",
            },
            {
                "date": "2024-01-03",
                "scope": "overall",
                "source_type": "__all__",
                "total_events": 0,
                "media_count": 1,
                "activity_score": 1,
                "tag_summary": [],
                "person_summary": [],
                "location_summary": [],
                "score_version": "v2",
            },
            {
                "date": "2024-01-03",
                "scope": "source_type",
                "source_type": "photo",
                "total_events": 0,
                "media_count": 1,
                "activity_score": 1,
                "tag_summary": [],
                "person_summary": [],
                "location_summary": [],
                "score_version": "v2",
            },
        ]
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_daily_aggregate_job_persists_derive_run_lifecycle_and_progress() -> None:
    workspace_root = _create_workspace_dir(prefix="daily-aggregate-run-lifecycle")
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
                        timestamp_start=datetime(2024, 1, 2, 8, 0, tzinfo=UTC),
                        timestamp_end=None,
                        title="Morning plan",
                        summary=None,
                        latitude=None,
                        longitude=None,
                        raw_payload={},
                        derived_payload={},
                    ),
                    Asset(
                        external_id="photo-1",
                        media_type="photo",
                        timestamp=datetime(2024, 1, 2, 9, 0, tzinfo=UTC),
                        summary=None,
                        latitude=None,
                        longitude=None,
                        metadata_json={},
                    ),
                ]
            )
            session.commit()

        snapshots: list[JobProgressSnapshot] = []
        result = DailyAggregateJob().run(
            runtime=runtime,
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 2),
            progress_callback=snapshots.append,
        )

        with runtime.session_factory() as session:
            job_run = session.execute(select(JobRun)).scalar_one()

        assert result.run_id == job_run.id
        assert job_run.type == "derive"
        assert job_run.job == "daily-aggregate"
        assert job_run.mode == "range"
        assert job_run.status == "completed"
        assert job_run.phase == "finalization"
        assert job_run.last_heartbeat_at is not None
        assert job_run.progress_json == {
            "total": 1,
            "completed": 1,
            "inserted": 3,
            "updated": 0,
            "unchanged": 0,
            "skipped": 0,
            "failed": 0,
            "missing_from_source": 0,
        }

        assert [
            snapshot.phase for snapshot in snapshots if snapshot.event == "phase_started"
        ] == [
            "loading canonical inputs",
            "building daily aggregates",
            "persisting daily aggregates",
            "finalization",
        ]
        assert snapshots[-1].event == "run_finished"
        assert snapshots[-1].job_type == "derive"
        assert snapshots[-1].job == "daily-aggregate"
        assert snapshots[-1].run_id == result.run_id
        assert snapshots[-1].inserted == 3
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def _serialize_aggregate(aggregate: DailyAggregate) -> dict[str, object]:
    """Return a compact, assertion-friendly aggregate representation."""

    return {
        "date": aggregate.date.isoformat(),
        "scope": aggregate.aggregate_scope,
        "source_type": aggregate.source_type,
        "total_events": aggregate.total_events,
        "media_count": aggregate.media_count,
        "activity_score": aggregate.activity_score,
        "tag_summary": aggregate.tag_summary_json,
        "person_summary": aggregate.person_summary_json,
        "location_summary": aggregate.location_summary_json,
        "score_version": aggregate.daily_view.metadata_json["score_version"],
    }


def _serialize_snapshot(snapshot) -> dict[str, object]:
    """Return a compact, assertion-friendly snapshot representation."""

    return {
        "date": snapshot.date.isoformat(),
        "scope": snapshot.daily_view.aggregate_scope,
        "source_type": (
            snapshot.daily_view.source_type
            if snapshot.daily_view.source_type is not None
            else DAILY_AGGREGATE_OVERALL_SOURCE_TYPE
        ),
        "total_events": snapshot.total_events,
        "media_count": snapshot.media_count,
        "activity_score": snapshot.activity_score,
        "tag_summary": snapshot.tag_summary_json,
        "person_summary": snapshot.person_summary_json,
        "location_summary": snapshot.location_summary_json,
        "score_version": snapshot.daily_view.metadata_json["score_version"],
    }


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
