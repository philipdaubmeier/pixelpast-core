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
from pixelpast.persistence.models import Asset, DailyAggregate, Event, Source
from pixelpast.persistence.session import session_scope
from pixelpast.shared.settings import Settings


def test_fastapi_app_exposes_health_endpoint() -> None:
    settings = Settings(database_url="sqlite://")
    app = create_app(settings=settings)

    with TestClient(app) as client:
        response = client.get("/health")

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
