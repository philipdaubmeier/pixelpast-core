"""Runtime foundation smoke tests."""

from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from alembic import command
from pixelpast.api.app import create_app
from pixelpast.persistence.base import Base
from pixelpast.persistence.models import (
    Asset,
    DAILY_AGGREGATE_SCOPE_OVERALL,
    DailyAggregate,
    DailyView,
    Event,
    EventPlace,
    JobRun,
    Place,
    Source,
)
from pixelpast.persistence.repositories import PlaceRepository, SourceRepository
from pixelpast.persistence.session import session_scope
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import Settings


def test_fastapi_app_exposes_health_endpoint() -> None:
    settings = Settings(database_url="sqlite://")
    app = create_app(settings=settings)

    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_non_api_session_scope_creates_session() -> None:
    settings = Settings(database_url="sqlite://")

    with session_scope(settings=settings) as session:
        value = session.execute(text("SELECT 1")).scalar_one()

    assert value == 1


def test_session_factory_is_available_on_app_state() -> None:
    settings = Settings(database_url="sqlite://")
    app = create_app(settings=settings)

    with app.state.session_factory() as session:
        value = session.execute(text("SELECT 1")).scalar_one()

    assert value == 1


def test_alembic_upgrade_head_runs() -> None:
    database_dir = Path("var")
    database_dir.mkdir(exist_ok=True)
    database_path = database_dir / f"test-alembic-{uuid4().hex}.db"
    config = Config("alembic.ini")
    config.attributes["database_url"] = f"sqlite:///{database_path.as_posix()}"

    try:
        command.upgrade(config, "head")
        assert database_path.exists()
        engine = create_engine(f"sqlite:///{database_path.as_posix()}")
        try:
            inspector = inspect(engine)

            assert set(inspector.get_table_names()) == {
                "alembic_version",
                "asset",
                "asset_person",
                "asset_tag",
                "daily_aggregate",
                "daily_view",
                "event",
                "event_asset",
                "event_place",
                "event_person",
                "event_tag",
                "import_run",
                "person",
                "person_group",
                "person_group_member",
                "place",
                "source",
                "tag",
            }
            assert {index["name"] for index in inspector.get_indexes("event")} == {
                "ix_event_source_id",
                "ix_event_timestamp_start",
                "ix_event_type",
            }
            assert {index["name"] for index in inspector.get_indexes("asset")} == {
                "ix_asset_timestamp",
            }
            asset_unique_constraints = inspector.get_unique_constraints("asset")
            assert {constraint["name"] for constraint in asset_unique_constraints} == {
                "uq_asset_external_id",
            }
            source_unique_constraints = inspector.get_unique_constraints("source")
            assert {
                constraint["name"] for constraint in source_unique_constraints
            } == {
                "uq_source_external_id",
                "uq_source_type_name",
            }
            source_columns = {
                column["name"] for column in inspector.get_columns("source")
            }
            place_columns = {
                column["name"] for column in inspector.get_columns("place")
            }
            event_place_columns = {
                column["name"] for column in inspector.get_columns("event_place")
            }
            import_run_columns = {
                column["name"] for column in inspector.get_columns("import_run")
            }
            daily_aggregate_columns = {
                column["name"] for column in inspector.get_columns("daily_aggregate")
            }
            daily_aggregate_indexes = {
                index["name"] for index in inspector.get_indexes("daily_aggregate")
            }
            place_indexes = {
                index["name"] for index in inspector.get_indexes("place")
            }
            place_unique_constraints = inspector.get_unique_constraints("place")
            event_place_pk = inspector.get_pk_constraint("event_place")
            daily_aggregate_pk = inspector.get_pk_constraint("daily_aggregate")
            daily_view_columns = {
                column["name"] for column in inspector.get_columns("daily_view")
            }
            assert {
                "type",
                "job",
                "phase",
                "last_heartbeat_at",
                "progress",
            } <= import_run_columns
            assert {"external_id", "name", "type", "config", "created_at"} <= source_columns
            assert place_columns == {
                "id",
                "source_id",
                "external_id",
                "display_name",
                "formatted_address",
                "latitude",
                "longitude",
                "lastupdate_at",
            }
            assert event_place_columns == {"event_id", "place_id", "confidence"}
            assert {
                "date",
                "daily_view_id",
                "total_events",
                "media_count",
                "activity_score",
                "color_value",
                "title",
                "tag_summary",
                "person_summary",
                "location_summary",
            } <= daily_aggregate_columns
            assert daily_view_columns == {
                "id",
                "aggregate_scope",
                "source_type",
                "label",
                "description",
                "metadata",
            }
            assert daily_aggregate_indexes == {
                "ix_daily_aggregate_view_date",
            }
            assert place_indexes == {
                "ix_place_lastupdate_at",
                "ix_place_latitude_longitude",
                "ix_place_source_external_id",
            }
            assert {
                constraint["name"] for constraint in place_unique_constraints
            } == {"uq_place_source_external_id"}
            assert event_place_pk["constrained_columns"] == ["event_id", "place_id"]
            assert daily_aggregate_pk["constrained_columns"] == ["date", "daily_view_id"]
        finally:
            engine.dispose()
    finally:
        if database_path.exists():
            database_path.unlink()


def test_metadata_contains_canonical_tables() -> None:
    assert set(Base.metadata.tables) == {
        "asset",
        "asset_person",
        "asset_tag",
        "daily_aggregate",
        "daily_view",
        "event",
        "event_asset",
        "event_place",
        "event_person",
        "event_tag",
        "import_run",
        "person",
        "person_group",
        "person_group_member",
        "place",
        "source",
        "tag",
    }


def test_utc_datetime_roundtrip_uses_aware_utc_values() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    event_timestamp = datetime(2026, 3, 11, 19, 15, tzinfo=timezone(timedelta(hours=2)))
    asset_timestamp = datetime(
        2026,
        3,
        11,
        7,
        15,
        tzinfo=timezone(timedelta(hours=-5)),
    )

    with Session(engine) as session:
        source = Source(
            name="Calendar",
            type="calendar",
            external_id="calendar-1",
            config={},
        )
        session.add(source)
        session.flush()
        session.add(
            Event(
                source_id=source.id,
                type="calendar",
                timestamp_start=event_timestamp,
                timestamp_end=None,
                title="Meeting",
                summary=None,
                latitude=None,
                longitude=None,
                raw_payload={},
                derived_payload={},
            )
        )
        session.add(
            Asset(
                external_id="photo-1",
                media_type="photo",
                timestamp=asset_timestamp,
                latitude=None,
                longitude=None,
                metadata_json={"camera": "phone"},
            )
        )
        session.commit()

    with Session(engine) as session:
        stored_event = session.query(Event).one()
        stored_asset = session.query(Asset).one()

    assert stored_event.timestamp_start.tzinfo is UTC
    assert stored_asset.timestamp.tzinfo is UTC
    assert stored_event.timestamp_start == datetime(2026, 3, 11, 17, 15, tzinfo=UTC)
    assert stored_asset.timestamp == datetime(2026, 3, 11, 12, 15, tzinfo=UTC)


def test_source_external_id_upgrade_keeps_existing_rows_nullable() -> None:
    database_dir = Path("var")
    database_dir.mkdir(exist_ok=True)
    database_path = database_dir / f"test-source-external-id-{uuid4().hex}.db"
    config = Config("alembic.ini")
    config.attributes["database_url"] = f"sqlite:///{database_path.as_posix()}"

    try:
        command.upgrade(config, "20260315_0007")
        engine = create_engine(f"sqlite:///{database_path.as_posix()}")
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        INSERT INTO source (id, name, type, config, created_at)
                        VALUES (
                            1,
                            'Photos',
                            'photos',
                            '{}',
                            '2026-03-15 12:00:00'
                        )
                        """
                    )
                )
        finally:
            engine.dispose()

        command.upgrade(config, "head")
        upgraded_engine = create_engine(f"sqlite:///{database_path.as_posix()}")
        try:
            with Session(upgraded_engine) as session:
                source = session.query(Source).one()

            assert source.name == "Photos"
            assert source.type == "photos"
            assert source.external_id is None
        finally:
            upgraded_engine.dispose()
    finally:
        if database_path.exists():
            database_path.unlink()


def test_source_repository_reconciles_sources_by_external_identity() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repository = SourceRepository(session)

        created = repository.get_or_create_by_external_id(
            external_id="calendar-123",
            name="Work Calendar",
            source_type="calendar",
            config={"origin_path": "/tmp/work.ics"},
        )
        created_id = created.id
        session.commit()

    with Session(engine) as session:
        repository = SourceRepository(session)
        persisted = repository.get_by_external_id(external_id="calendar-123")

        assert persisted is not None
        assert persisted.id == created_id
        assert persisted.name == "Work Calendar"
        assert persisted.type == "calendar"
        assert persisted.external_id == "calendar-123"
        assert persisted.config == {"origin_path": "/tmp/work.ics"}

        updated = repository.get_or_create_by_external_id(
            external_id="calendar-123",
            name="Renamed Calendar",
            source_type="calendar",
            config={
                "origin_path": "/tmp/archive.zip",
                "archive_member_path": "nested/work.ics",
            },
        )
        session.commit()

        assert updated.id == persisted.id

    with Session(engine) as session:
        sources = list(session.query(Source).all())

    assert len(sources) == 1
    assert sources[0].name == "Renamed Calendar"
    assert sources[0].external_id == "calendar-123"
    assert sources[0].config == {
        "origin_path": "/tmp/archive.zip",
        "archive_member_path": "nested/work.ics",
    }


def test_place_repository_upserts_provider_scoped_place_and_event_place_links() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    refreshed_at = datetime(2026, 3, 22, 10, 15, tzinfo=UTC)
    second_refresh = datetime(2026, 3, 23, 8, 30, tzinfo=UTC)

    with Session(engine) as session:
        source = Source(
            name="Google Places API",
            type="google_places_api",
            external_id="google_places_api",
            config={},
        )
        event_source = Source(
            name="Timeline",
            type="google_maps_timeline",
            external_id="timeline-source",
            config={},
        )
        session.add_all([source, event_source])
        session.flush()
        event = Event(
            source_id=event_source.id,
            type="timeline_visit",
            timestamp_start=datetime(2026, 3, 22, 9, 0, tzinfo=UTC),
            timestamp_end=None,
            title="Cafe visit",
            summary=None,
            latitude=52.52,
            longitude=13.405,
            raw_payload={"googlePlaceId": "places/123"},
            derived_payload={},
        )
        session.add(event)
        session.flush()
        source_id = source.id
        event_id = event.id

        repository = PlaceRepository(session)
        inserted_place = repository.upsert(
            source_id=source_id,
            external_id="places/123",
            display_name="Cafe Central",
            formatted_address="Mitte, Berlin",
            latitude=52.52,
            longitude=13.405,
            lastupdate_at=refreshed_at,
        )
        unchanged_place = repository.upsert(
            source_id=source_id,
            external_id="places/123",
            display_name="Cafe Central",
            formatted_address="Mitte, Berlin",
            latitude=52.52,
            longitude=13.405,
            lastupdate_at=refreshed_at,
        )
        updated_place = repository.upsert(
            source_id=source_id,
            external_id="places/123",
            display_name="Cafe Central Berlin",
            formatted_address="Mitte, Berlin, Germany",
            latitude=52.5201,
            longitude=13.4051,
            lastupdate_at=second_refresh,
        )

        inserted_link = repository.upsert_event_place_link(
            event_id=event_id,
            place_id=inserted_place.place.id,
            confidence=0.87,
        )
        unchanged_link = repository.upsert_event_place_link(
            event_id=event_id,
            place_id=inserted_place.place.id,
            confidence=0.87,
        )
        updated_link = repository.upsert_event_place_link(
            event_id=event_id,
            place_id=inserted_place.place.id,
            confidence=None,
        )
        fetched_place = repository.get_by_source_and_external_id(
            source_id=source_id,
            external_id="places/123",
        )
        fetched_links = repository.list_event_place_links(
            event_ids=[event_id],
            place_ids=[inserted_place.place.id],
        )
        fetched_link_rows = [
            (link.event_id, link.place_id, link.confidence) for link in fetched_links
        ]
        session.commit()

    with Session(engine) as session:
        stored_place = session.query(Place).one()
        stored_link = session.query(EventPlace).one()

    assert inserted_place.status == "inserted"
    assert unchanged_place.status == "unchanged"
    assert updated_place.status == "updated"
    assert inserted_link.status == "inserted"
    assert unchanged_link.status == "unchanged"
    assert updated_link.status == "updated"
    assert fetched_place is not None
    assert fetched_link_rows == [(event_id, stored_place.id, None)]
    assert stored_place.source_id == source_id
    assert stored_place.external_id == "places/123"
    assert stored_place.display_name == "Cafe Central Berlin"
    assert stored_place.formatted_address == "Mitte, Berlin, Germany"
    assert stored_place.latitude == 52.5201
    assert stored_place.longitude == 13.4051
    assert stored_place.lastupdate_at == second_refresh
    assert stored_link.event_id == event_id
    assert stored_link.place_id == stored_place.id
    assert stored_link.confidence is None


def test_daily_aggregate_date_roundtrip_uses_python_date() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        daily_view = DailyView(
            aggregate_scope=DAILY_AGGREGATE_SCOPE_OVERALL,
            source_type=None,
            label="Activity",
            description="Default heat intensity across all timeline sources.",
            metadata_json={"score_version": "v1"},
        )
        session.add(daily_view)
        session.flush()
        session.add(
            DailyAggregate(
                date=datetime(2026, 3, 11, tzinfo=UTC).date(),
                daily_view_id=daily_view.id,
                total_events=2,
                media_count=1,
                activity_score=3,
                color_value="#2F2FAB",
                title="V",
            )
        )
        session.commit()

    with Session(engine) as session:
        stored_aggregate = session.query(DailyAggregate).one()

    assert stored_aggregate.date.isoformat() == "2026-03-11"
    assert stored_aggregate.aggregate_scope == DAILY_AGGREGATE_SCOPE_OVERALL
    assert stored_aggregate.color_value == "#2F2FAB"
    assert stored_aggregate.title == "V"
    assert stored_aggregate.daily_view.source_type is None
    assert stored_aggregate.tag_summary_json == []
    assert stored_aggregate.person_summary_json == []
    assert stored_aggregate.location_summary_json == []


def test_daily_aggregate_schema_v2_upgrade_backfills_legacy_rows() -> None:
    database_dir = Path("var")
    database_dir.mkdir(exist_ok=True)
    database_path = database_dir / f"test-daily-aggregate-v2-{uuid4().hex}.db"
    config = Config("alembic.ini")
    config.attributes["database_url"] = f"sqlite:///{database_path.as_posix()}"

    try:
        command.upgrade(config, "20260313_0005")
        engine = create_engine(f"sqlite:///{database_path.as_posix()}")
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        INSERT INTO daily_aggregate (
                            date,
                            total_events,
                            media_count,
                            activity_score,
                            metadata
                        )
                        VALUES (
                            '2024-01-02',
                            2,
                            1,
                            3,
                            '{"score_version": "v1"}'
                        )
                        """
                    )
                )
        finally:
            engine.dispose()

        command.upgrade(config, "head")
        upgraded_engine = create_engine(f"sqlite:///{database_path.as_posix()}")
        try:
            with Session(upgraded_engine) as session:
                stored_aggregate = session.query(DailyAggregate).one()
                stored_daily_view = session.query(DailyView).one()

            assert stored_aggregate.date.isoformat() == "2024-01-02"
            assert stored_aggregate.aggregate_scope == DAILY_AGGREGATE_SCOPE_OVERALL
            assert stored_aggregate.daily_view.source_type is None
            assert stored_aggregate.daily_view_id == stored_daily_view.id
            assert stored_aggregate.total_events == 2
            assert stored_aggregate.media_count == 1
            assert stored_aggregate.activity_score == 3
            assert stored_aggregate.color_value is None
            assert stored_aggregate.title is None
            assert stored_aggregate.tag_summary_json == []
            assert stored_aggregate.person_summary_json == []
            assert stored_aggregate.location_summary_json == []
            assert stored_daily_view.aggregate_scope == DAILY_AGGREGATE_SCOPE_OVERALL
            assert stored_daily_view.source_type is None
            assert stored_daily_view.label == "Activity"
            assert stored_daily_view.metadata_json == {
                "score_version": "v1",
                "activity_score_color_thresholds": [
                    {"activity_score": 1, "color_value": "low"},
                    {"activity_score": 35, "color_value": "medium"},
                    {"activity_score": 70, "color_value": "high"},
                ],
            }
            assert (
                stored_daily_view.description
                == "Default heat intensity across all timeline sources."
            )
        finally:
            upgraded_engine.dispose()
    finally:
        if database_path.exists():
            database_path.unlink()


def test_daily_aggregate_color_title_schema_upgrade_backfills_existing_rows() -> None:
    database_dir = Path("var")
    database_dir.mkdir(exist_ok=True)
    database_path = database_dir / f"test-daily-aggregate-color-title-{uuid4().hex}.db"
    config = Config("alembic.ini")
    config.attributes["database_url"] = f"sqlite:///{database_path.as_posix()}"

    try:
        command.upgrade(config, "20260316_0012")
        engine = create_engine(f"sqlite:///{database_path.as_posix()}")
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        INSERT INTO daily_view (
                            id,
                            aggregate_scope,
                            source_type,
                            label,
                            description,
                            metadata
                        )
                        VALUES (
                            1,
                            'overall',
                            NULL,
                            'Activity',
                            'Default heat intensity across all timeline sources.',
                            '{"score_version": "v2", "activity_score_color_thresholds": []}'
                        )
                        """
                    )
                )
                connection.execute(
                    text(
                        """
                        INSERT INTO daily_aggregate (
                            date,
                            daily_view_id,
                            total_events,
                            media_count,
                            activity_score,
                            tag_summary,
                            person_summary,
                            location_summary
                        )
                        VALUES (
                            '2024-01-02',
                            1,
                            2,
                            1,
                            3,
                            '[]',
                            '[]',
                            '[]'
                        )
                        """
                    )
                )
        finally:
            engine.dispose()

        command.upgrade(config, "head")
        upgraded_engine = create_engine(f"sqlite:///{database_path.as_posix()}")
        try:
            with Session(upgraded_engine) as session:
                stored_aggregate = session.query(DailyAggregate).one()

            assert stored_aggregate.date.isoformat() == "2024-01-02"
            assert stored_aggregate.color_value is None
            assert stored_aggregate.title is None
            assert stored_aggregate.activity_score == 3
        finally:
            upgraded_engine.dispose()
    finally:
        if database_path.exists():
            database_path.unlink()


def test_job_run_generalization_upgrade_backfills_existing_ingest_rows() -> None:
    database_dir = Path("var")
    database_dir.mkdir(exist_ok=True)
    database_path = database_dir / f"test-job-run-generalization-{uuid4().hex}.db"
    config = Config("alembic.ini")
    config.attributes["database_url"] = f"sqlite:///{database_path.as_posix()}"

    try:
        command.upgrade(config, "20260314_0006")
        engine = create_engine(f"sqlite:///{database_path.as_posix()}")
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        INSERT INTO source (id, name, type, config, created_at)
                        VALUES (
                            1,
                            'Photos',
                            'photos',
                            '{}',
                            '2026-03-14 10:00:00'
                        )
                        """
                    )
                )
                connection.execute(
                    text(
                        """
                        INSERT INTO import_run (
                            source_id,
                            started_at,
                            finished_at,
                            status,
                            mode,
                            phase,
                            last_heartbeat_at,
                            progress
                        )
                        VALUES (
                            1,
                            '2026-03-14 10:00:00',
                            '2026-03-14 10:05:00',
                            'completed',
                            'full',
                            'finalization',
                            '2026-03-14 10:05:00',
                            '{"total": 1, "completed": 1, "inserted": 3, "updated": 0, "unchanged": 0, "skipped": 0, "failed": 0, "missing_from_source": 0}'
                        )
                        """
                    )
                )
        finally:
            engine.dispose()

        command.upgrade(config, "head")
        upgraded_engine = create_engine(f"sqlite:///{database_path.as_posix()}")
        try:
            with Session(upgraded_engine) as session:
                job_run = session.query(JobRun).one()

            assert job_run.type == "ingest"
            assert job_run.job == "photos"
            assert job_run.status == "completed"
            assert job_run.mode == "full"
            assert job_run.phase == "finalization"
            assert job_run.progress_json is not None
            assert job_run.progress_json["inserted"] == 3
        finally:
            upgraded_engine.dispose()
    finally:
        if database_path.exists():
            database_path.unlink()


def test_initialize_database_runs_alembic_for_file_database() -> None:
    database_dir = Path("var")
    database_dir.mkdir(exist_ok=True)
    database_path = database_dir / f"test-runtime-init-{uuid4().hex}.db"

    try:
        runtime = create_runtime_context(
            settings=Settings(database_url=f"sqlite:///{database_path.as_posix()}")
        )
        try:
            initialize_database(runtime)
        finally:
            runtime.engine.dispose()

        upgraded_engine = create_engine(f"sqlite:///{database_path.as_posix()}")
        try:
            inspector = inspect(upgraded_engine)
            import_run_columns = {
                column["name"] for column in inspector.get_columns("import_run")
            }
            assert "alembic_version" in inspector.get_table_names()
        finally:
            upgraded_engine.dispose()

        assert {
            "type",
            "job",
            "phase",
            "last_heartbeat_at",
            "progress",
        } <= import_run_columns
    finally:
        if database_path.exists():
            database_path.unlink()
