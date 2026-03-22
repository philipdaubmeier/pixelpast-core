"""End-to-end tests for the Google Places derive job."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from pixelpast.analytics.google_places import (
    GooglePlaceSnapshot,
    GooglePlacesClientError,
    GooglePlacesJob,
)
from pixelpast.cli.main import app
from pixelpast.persistence.models import Event, EventPlace, JobRun, Place, Source
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import Settings, get_settings
from typer.testing import CliRunner

runner = CliRunner()


class FakeGooglePlacesClient:
    """Deterministic stub client used by Google Places derive tests."""

    def __init__(
        self,
        responses_by_place_id: dict[str, GooglePlaceSnapshot],
        calls: list[str],
        *,
        error_place_id: str | None = None,
    ) -> None:
        self._responses_by_place_id = responses_by_place_id
        self._calls = calls
        self._error_place_id = error_place_id

    def fetch_place(self, *, place_id: str) -> GooglePlaceSnapshot:
        self._calls.append(place_id)
        if self._error_place_id == place_id:
            raise GooglePlacesClientError(f"fetch failed for {place_id}")
        return self._responses_by_place_id[place_id]


def test_google_places_job_resolves_places_reuses_cache_and_is_idempotent() -> None:
    database_path = _build_test_database_path("google-places-job")
    initial_refresh_at = datetime(2026, 3, 22, 12, 30, tzinfo=UTC)
    second_refresh_at = datetime(2026, 3, 22, 13, 0, tzinfo=UTC)
    fetch_calls: list[str] = []
    responses = {
        "places/new": GooglePlaceSnapshot(
            external_id="places/new",
            display_name="New Bakery",
            formatted_address="Hamburg, Germany",
            latitude=53.5511,
            longitude=9.9937,
        ),
        "places/stale": GooglePlaceSnapshot(
            external_id="places/stale",
            display_name="Musee D'Orsay",
            formatted_address="Paris, France",
            latitude=48.86,
            longitude=2.3266,
        ),
    }

    runtime = _create_runtime(
        database_path=database_path,
        api_key="secret-key",
    )
    try:
        initialize_database(runtime)
        with runtime.session_factory() as session:
            seeded = _seed_google_places_scenario(session=session)

        job = GooglePlacesJob(
            client_factory=lambda settings: FakeGooglePlacesClient(
                responses,
                fetch_calls,
            ),
            refreshed_at_factory=lambda: initial_refresh_at,
        )
        first_result = job.run(runtime=runtime)

        assert first_result.mode == "full"
        assert first_result.status == "completed"
        assert first_result.scanned_event_count == 5
        assert first_result.qualifying_event_count == 4
        assert first_result.unique_place_id_count == 3
        assert first_result.remote_fetch_count == 2
        assert first_result.cached_reuse_count == 1
        assert first_result.inserted_place_count == 1
        assert first_result.updated_place_count == 1
        assert first_result.unchanged_place_count == 1
        assert first_result.inserted_event_place_link_count == 4
        assert first_result.updated_event_place_link_count == 0
        assert first_result.unchanged_event_place_link_count == 0
        assert fetch_calls == ["places/new", "places/stale"]

        with runtime.session_factory() as session:
            places = {
                place.external_id: place
                for place in session.execute(
                    select(Place).order_by(Place.external_id)
                ).scalars()
            }
            event_links = list(
                session.execute(
                    select(EventPlace).order_by(EventPlace.event_id, EventPlace.place_id)
                ).scalars()
            )
            first_job_run = session.execute(
                select(JobRun).order_by(JobRun.id.desc())
            ).scalar_one()

        assert sorted(places) == ["places/fresh", "places/new", "places/stale"]
        assert places["places/fresh"].display_name == "Fresh Cafe"
        assert places["places/new"].lastupdate_at == initial_refresh_at
        assert places["places/stale"].display_name == "Musee D'Orsay"
        assert places["places/stale"].lastupdate_at == initial_refresh_at
        assert [
            (link.event_id, link.place_id, link.confidence)
            for link in event_links
        ] == [
            (seeded["event_ids"]["fresh_primary"], places["places/fresh"].id, 0.9),
            (seeded["event_ids"]["fresh_repeat"], places["places/fresh"].id, None),
            (seeded["event_ids"]["stale"], places["places/stale"].id, 0.4),
            (seeded["event_ids"]["new"], places["places/new"].id, None),
        ]
        assert first_job_run.status == "completed"
        assert first_job_run.phase == "finalization"
        assert first_job_run.progress_json == {
            "total": 1,
            "completed": 1,
            "inserted": 1,
            "updated": 1,
            "unchanged": 1,
            "skipped": 0,
            "failed": 0,
            "missing_from_source": 0,
        }

        second_result = GooglePlacesJob(
            client_factory=lambda settings: FakeGooglePlacesClient(
                responses,
                fetch_calls,
            ),
            refreshed_at_factory=lambda: second_refresh_at,
        ).run(runtime=runtime)

        assert second_result.remote_fetch_count == 0
        assert second_result.cached_reuse_count == 3
        assert second_result.inserted_place_count == 0
        assert second_result.updated_place_count == 0
        assert second_result.unchanged_place_count == 3
        assert second_result.inserted_event_place_link_count == 0
        assert second_result.updated_event_place_link_count == 0
        assert second_result.unchanged_event_place_link_count == 4
        assert fetch_calls == ["places/new", "places/stale"]
    finally:
        runtime.engine.dispose()
        if database_path.exists():
            database_path.unlink()


def test_google_places_job_fails_when_configuration_is_missing() -> None:
    database_path = _build_test_database_path("google-places-job-missing-config")
    runtime = _create_runtime(database_path=database_path, api_key=None)
    try:
        initialize_database(runtime)
        with runtime.session_factory() as session:
            _seed_google_places_scenario(session=session)

        with pytest.raises(ValueError) as error:
            GooglePlacesJob().run(runtime=runtime)

        assert "PIXELPAST_GOOGLE_PLACES_API_KEY" in str(error.value)
        with runtime.session_factory() as session:
            job_runs = list(session.execute(select(JobRun).order_by(JobRun.id.desc())).scalars())
        assert job_runs == []
    finally:
        runtime.engine.dispose()
        if database_path.exists():
            database_path.unlink()


def test_google_places_job_fails_when_provider_request_errors() -> None:
    database_path = _build_test_database_path("google-places-job-provider-failure")
    fetch_calls: list[str] = []
    runtime = _create_runtime(database_path=database_path, api_key="secret-key")
    try:
        initialize_database(runtime)
        with runtime.session_factory() as session:
            _seed_google_places_scenario(session=session)

        with pytest.raises(GooglePlacesClientError):
            GooglePlacesJob(
                client_factory=lambda settings: FakeGooglePlacesClient(
                    {
                        "places/new": GooglePlaceSnapshot(
                            external_id="places/new",
                            display_name="New Bakery",
                            formatted_address="Hamburg, Germany",
                            latitude=53.5511,
                            longitude=9.9937,
                        ),
                        "places/stale": GooglePlaceSnapshot(
                            external_id="places/stale",
                            display_name="Musee D'Orsay",
                            formatted_address="Paris, France",
                            latitude=48.86,
                            longitude=2.3266,
                        ),
                    },
                    fetch_calls,
                    error_place_id="places/new",
                )
            ).run(runtime=runtime)

        assert fetch_calls == ["places/new"]
        with runtime.session_factory() as session:
            places = list(session.execute(select(Place).order_by(Place.external_id)).scalars())
            event_places = list(session.execute(select(EventPlace)).scalars())
            job_run = session.execute(select(JobRun).order_by(JobRun.id.desc())).scalar_one()
        assert [place.external_id for place in places] == ["places/fresh", "places/stale"]
        assert event_places == []
        assert job_run.status == "failed"
        assert job_run.phase == "fetching place details"
        assert job_run.progress_json is not None
        assert job_run.progress_json["failed"] == 1
    finally:
        runtime.engine.dispose()
        if database_path.exists():
            database_path.unlink()


def test_google_places_job_can_limit_processed_place_ids() -> None:
    database_path = _build_test_database_path("google-places-job-top-place-ids")
    fetch_calls: list[str] = []
    runtime = _create_runtime(database_path=database_path, api_key="secret-key")
    try:
        initialize_database(runtime)
        with runtime.session_factory() as session:
            _seed_google_places_scenario(session=session)

        result = GooglePlacesJob(
            client_factory=lambda settings: FakeGooglePlacesClient(
                {
                    "places/new": GooglePlaceSnapshot(
                        external_id="places/new",
                        display_name="New Bakery",
                        formatted_address="Hamburg, Germany",
                        latitude=53.5511,
                        longitude=9.9937,
                    ),
                    "places/stale": GooglePlaceSnapshot(
                        external_id="places/stale",
                        display_name="Musee D'Orsay",
                        formatted_address="Paris, France",
                        latitude=48.86,
                        longitude=2.3266,
                    ),
                },
                fetch_calls,
            )
        ).run(runtime=runtime, max_place_ids=2)

        assert result.scanned_event_count == 5
        assert result.qualifying_event_count == 3
        assert result.unique_place_id_count == 2
        assert result.remote_fetch_count == 1
        assert result.cached_reuse_count == 1
        assert fetch_calls == ["places/new"]
    finally:
        runtime.engine.dispose()
        if database_path.exists():
            database_path.unlink()


def test_cli_derive_google_places_prints_progress_and_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    database_path = _build_test_database_path("cli-google-places")
    monkeypatch.setenv(
        "PIXELPAST_DATABASE_URL",
        f"sqlite:///{database_path.as_posix()}",
    )
    monkeypatch.setenv("PIXELPAST_GOOGLE_PLACES_API_KEY", "secret-key")
    get_settings.cache_clear()

    job_module = pytest.importorskip("pixelpast.analytics.google_places.job")
    fetch_calls: list[str] = []

    def fake_client_factory(settings: Settings) -> FakeGooglePlacesClient:
        return FakeGooglePlacesClient(
            {
                "places/new": GooglePlaceSnapshot(
                    external_id="places/new",
                    display_name="New Bakery",
                    formatted_address="Hamburg, Germany",
                    latitude=53.5511,
                    longitude=9.9937,
                ),
                "places/stale": GooglePlaceSnapshot(
                    external_id="places/stale",
                    display_name="Musee D'Orsay",
                    formatted_address="Paris, France",
                    latitude=48.86,
                    longitude=2.3266,
                ),
            },
            fetch_calls,
        )

    monkeypatch.setattr(job_module, "_build_google_places_client", fake_client_factory)

    runtime = create_runtime_context(settings=get_settings())
    try:
        initialize_database(runtime)
        with runtime.session_factory() as session:
            _seed_google_places_scenario(session=session)
    finally:
        runtime.engine.dispose()

    try:
        result = runner.invoke(app, ["derive", "google_places"])

        assert result.exit_code == 0
        assert "[google_places] completed" in result.stdout
        assert "collecting place ids" in result.stdout
        assert "fetching place details" in result.stdout
        assert "persisting places and links" in result.stdout
        assert "inserted: 1" in result.stdout
        assert "updated: 1" in result.stdout
        assert "unchanged: 1" in result.stdout
        assert "skipped: 0" in result.stdout
        assert "failed: 0" in result.stdout
        assert "missing_from_source: 0" in result.stdout
        assert "scanned_event_count:" not in result.stdout
        assert fetch_calls == ["places/new", "places/stale"]
    finally:
        get_settings.cache_clear()
        if database_path.exists():
            database_path.unlink()


def test_cli_derive_google_places_top_place_ids_limits_work(monkeypatch: pytest.MonkeyPatch) -> None:
    database_path = _build_test_database_path("cli-google-places-top-place-ids")
    monkeypatch.setenv(
        "PIXELPAST_DATABASE_URL",
        f"sqlite:///{database_path.as_posix()}",
    )
    monkeypatch.setenv("PIXELPAST_GOOGLE_PLACES_API_KEY", "secret-key")
    get_settings.cache_clear()

    job_module = pytest.importorskip("pixelpast.analytics.google_places.job")
    fetch_calls: list[str] = []

    def fake_client_factory(settings: Settings) -> FakeGooglePlacesClient:
        return FakeGooglePlacesClient(
            {
                "places/new": GooglePlaceSnapshot(
                    external_id="places/new",
                    display_name="New Bakery",
                    formatted_address="Hamburg, Germany",
                    latitude=53.5511,
                    longitude=9.9937,
                ),
                "places/stale": GooglePlaceSnapshot(
                    external_id="places/stale",
                    display_name="Musee D'Orsay",
                    formatted_address="Paris, France",
                    latitude=48.86,
                    longitude=2.3266,
                ),
            },
            fetch_calls,
        )

    monkeypatch.setattr(job_module, "_build_google_places_client", fake_client_factory)

    runtime = create_runtime_context(settings=get_settings())
    try:
        initialize_database(runtime)
        with runtime.session_factory() as session:
            _seed_google_places_scenario(session=session)
    finally:
        runtime.engine.dispose()

    try:
        result = runner.invoke(app, ["derive", "google_places", "--top-place-ids", "2"])

        assert result.exit_code == 0
        assert "inserted: 1" in result.stdout
        assert "updated: 0" in result.stdout
        assert "unchanged: 1" in result.stdout
        assert "qualifying_event_count:" not in result.stdout
        assert fetch_calls == ["places/new"]
    finally:
        get_settings.cache_clear()
        if database_path.exists():
            database_path.unlink()


def test_cli_derive_google_places_returns_expected_exit_codes_on_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_config_database_path = _build_test_database_path(
        "cli-google-places-missing-config"
    )
    monkeypatch.setenv(
        "PIXELPAST_DATABASE_URL",
        f"sqlite:///{missing_config_database_path.as_posix()}",
    )
    monkeypatch.delenv("PIXELPAST_GOOGLE_PLACES_API_KEY", raising=False)
    get_settings.cache_clear()

    runtime = create_runtime_context(settings=get_settings())
    try:
        initialize_database(runtime)
        with runtime.session_factory() as session:
            _seed_google_places_scenario(session=session)
    finally:
        runtime.engine.dispose()

    result = runner.invoke(app, ["derive", "google_places"])
    assert result.exit_code == 2
    assert "error: Google Places derivation requires" in result.stderr

    provider_failure_database_path = _build_test_database_path(
        "cli-google-places-provider-failure"
    )
    monkeypatch.setenv(
        "PIXELPAST_DATABASE_URL",
        f"sqlite:///{provider_failure_database_path.as_posix()}",
    )
    monkeypatch.setenv("PIXELPAST_GOOGLE_PLACES_API_KEY", "secret-key")
    get_settings.cache_clear()

    job_module = pytest.importorskip("pixelpast.analytics.google_places.job")

    def failing_client_factory(settings: Settings) -> FakeGooglePlacesClient:
        return FakeGooglePlacesClient(
            {
                "places/new": GooglePlaceSnapshot(
                    external_id="places/new",
                    display_name="New Bakery",
                    formatted_address="Hamburg, Germany",
                    latitude=53.5511,
                    longitude=9.9937,
                ),
                "places/stale": GooglePlaceSnapshot(
                    external_id="places/stale",
                    display_name="Musee D'Orsay",
                    formatted_address="Paris, France",
                    latitude=48.86,
                    longitude=2.3266,
                ),
            },
            [],
            error_place_id="places/new",
        )

    monkeypatch.setattr(job_module, "_build_google_places_client", failing_client_factory)

    runtime = create_runtime_context(settings=get_settings())
    try:
        initialize_database(runtime)
        with runtime.session_factory() as session:
            _seed_google_places_scenario(session=session)
    finally:
        runtime.engine.dispose()

    try:
        result = runner.invoke(app, ["derive", "google_places"])
        assert result.exit_code == 1
        assert "error: fetch failed for places/new" in result.stderr
    finally:
        get_settings.cache_clear()
        for path in (missing_config_database_path, provider_failure_database_path):
            if path.exists():
                path.unlink()


def _create_runtime(*, database_path: Path, api_key: str | None) -> object:
    settings_kwargs = {"database_url": f"sqlite:///{database_path.as_posix()}"}
    if api_key is not None:
        settings_kwargs["google_places_api_key"] = api_key
    return create_runtime_context(settings=Settings(**settings_kwargs))


def _seed_google_places_scenario(*, session: Session) -> dict[str, dict[str, int]]:
    reference_now = datetime(2026, 3, 22, 12, 0, tzinfo=UTC)
    provider_source = Source(
        name="Google Places API",
        type="google_places_api",
        external_id="google_places_api",
        config={},
    )
    timeline_source = Source(
        name="Timeline",
        type="google_maps_timeline",
        external_id="timeline-source",
        config={},
    )
    session.add_all([provider_source, timeline_source])
    session.flush()

    fresh_primary = Event(
        source_id=timeline_source.id,
        type="timeline_visit",
        timestamp_start=datetime(2026, 3, 20, 9, 0, tzinfo=UTC),
        timestamp_end=None,
        title="Fresh visit",
        summary=None,
        latitude=None,
        longitude=None,
        raw_payload={
            "googlePlaceId": "places/fresh",
            "candidateProbability": 0.9,
        },
        derived_payload={},
    )
    fresh_repeat = Event(
        source_id=timeline_source.id,
        type="timeline_visit",
        timestamp_start=datetime(2026, 3, 20, 10, 0, tzinfo=UTC),
        timestamp_end=None,
        title="Fresh revisit",
        summary=None,
        latitude=None,
        longitude=None,
        raw_payload={"googlePlaceId": "places/fresh"},
        derived_payload={},
    )
    stale = Event(
        source_id=timeline_source.id,
        type="timeline_visit",
        timestamp_start=datetime(2026, 3, 21, 8, 0, tzinfo=UTC),
        timestamp_end=None,
        title="Stale visit",
        summary=None,
        latitude=None,
        longitude=None,
        raw_payload={
            "googlePlaceId": "places/stale",
            "candidateProbability": "0.4",
        },
        derived_payload={},
    )
    new = Event(
        source_id=timeline_source.id,
        type="timeline_visit",
        timestamp_start=datetime(2026, 3, 22, 7, 0, tzinfo=UTC),
        timestamp_end=None,
        title="New visit",
        summary=None,
        latitude=None,
        longitude=None,
        raw_payload={"googlePlaceId": "places/new"},
        derived_payload={},
    )
    ignored = Event(
        source_id=timeline_source.id,
        type="timeline_activity",
        timestamp_start=datetime(2026, 3, 22, 9, 0, tzinfo=UTC),
        timestamp_end=None,
        title="Ignored",
        summary=None,
        latitude=None,
        longitude=None,
        raw_payload={},
        derived_payload={},
    )
    session.add_all([fresh_primary, fresh_repeat, stale, new, ignored])
    session.flush()

    session.add_all(
        [
            Place(
                source_id=provider_source.id,
                external_id="places/fresh",
                display_name="Fresh Cafe",
                formatted_address="Berlin",
                latitude=52.52,
                longitude=13.405,
                lastupdate_at=reference_now - timedelta(days=10),
            ),
            Place(
                source_id=provider_source.id,
                external_id="places/stale",
                display_name="Old Museum",
                formatted_address="Paris",
                latitude=48.8566,
                longitude=2.3522,
                lastupdate_at=reference_now - timedelta(days=1200),
            ),
        ]
    )
    session.commit()

    return {
        "event_ids": {
            "fresh_primary": fresh_primary.id,
            "fresh_repeat": fresh_repeat.id,
            "stale": stale.id,
            "new": new.id,
        }
    }


def _build_test_database_path(prefix: str) -> Path:
    database_dir = Path("var")
    database_dir.mkdir(exist_ok=True)
    return database_dir / f"{prefix}-{uuid4().hex}.db"
