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
    DAILY_AGGREGATE_OVERALL_SOURCE_TYPE,
    DAILY_AGGREGATE_SCOPE_OVERALL,
    DailyAggregate,
    Event,
    JobRun,
    Source,
)
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
                "event",
                "event_asset",
                "event_person",
                "event_tag",
                "import_run",
                "person",
                "person_group",
                "person_group_member",
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
                "uq_source_type_name",
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
            daily_aggregate_pk = inspector.get_pk_constraint("daily_aggregate")
            assert {
                "type",
                "job",
                "phase",
                "last_heartbeat_at",
                "progress",
            } <= import_run_columns
            assert {
                "date",
                "aggregate_scope",
                "source_type",
                "total_events",
                "media_count",
                "activity_score",
                "tag_summary",
                "person_summary",
                "location_summary",
                "metadata",
            } <= daily_aggregate_columns
            assert daily_aggregate_indexes == {"ix_daily_aggregate_scope_date"}
            assert daily_aggregate_pk["constrained_columns"] == [
                "date",
                "aggregate_scope",
                "source_type",
            ]
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
        "event",
        "event_asset",
        "event_person",
        "event_tag",
        "import_run",
        "person",
        "person_group",
        "person_group_member",
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
        source = Source(name="Calendar", type="calendar", config={})
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


def test_daily_aggregate_date_roundtrip_uses_python_date() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            DailyAggregate(
                date=datetime(2026, 3, 11, tzinfo=UTC).date(),
                total_events=2,
                media_count=1,
                activity_score=3,
                metadata_json={"score_version": "v1"},
            )
        )
        session.commit()

    with Session(engine) as session:
        stored_aggregate = session.query(DailyAggregate).one()

    assert stored_aggregate.date.isoformat() == "2026-03-11"
    assert stored_aggregate.aggregate_scope == DAILY_AGGREGATE_SCOPE_OVERALL
    assert stored_aggregate.source_type == DAILY_AGGREGATE_OVERALL_SOURCE_TYPE
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

            assert stored_aggregate.date.isoformat() == "2024-01-02"
            assert stored_aggregate.aggregate_scope == DAILY_AGGREGATE_SCOPE_OVERALL
            assert (
                stored_aggregate.source_type
                == DAILY_AGGREGATE_OVERALL_SOURCE_TYPE
            )
            assert stored_aggregate.total_events == 2
            assert stored_aggregate.media_count == 1
            assert stored_aggregate.activity_score == 3
            assert stored_aggregate.tag_summary_json == []
            assert stored_aggregate.person_summary_json == []
            assert stored_aggregate.location_summary_json == []
            assert stored_aggregate.metadata_json == {"score_version": "v1"}
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
