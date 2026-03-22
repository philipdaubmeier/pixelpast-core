"""Tests for Google Places derive loading, provider identity, and client boundaries."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from pixelpast.analytics.google_places import (
    GooglePlacesCanonicalLoader,
    GooglePlacesClient,
    GooglePlacesClientHttpError,
    GooglePlacesClientResponseError,
    GooglePlacesProviderSourceResolver,
    GooglePlacesResponse,
)
from pixelpast.persistence.base import Base
from pixelpast.persistence.models import Event, Place, Source
from pixelpast.persistence.repositories import PlaceRepository, SourceRepository
from pixelpast.shared.settings import Settings


def test_google_places_loader_builds_deduplicated_refresh_plan() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    reference_now = datetime(2026, 3, 22, 12, 0, tzinfo=UTC)

    with Session(engine) as session:
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

        session.add_all(
            [
                Event(
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
                ),
                Event(
                    source_id=timeline_source.id,
                    type="timeline_visit",
                    timestamp_start=datetime(2026, 3, 20, 10, 0, tzinfo=UTC),
                    timestamp_end=None,
                    title="Fresh revisit",
                    summary=None,
                    latitude=None,
                    longitude=None,
                    raw_payload={
                        "googlePlaceId": "places/fresh",
                        "candidateProbability": "0.4",
                    },
                    derived_payload={},
                ),
                Event(
                    source_id=timeline_source.id,
                    type="timeline_visit",
                    timestamp_start=datetime(2026, 3, 21, 8, 0, tzinfo=UTC),
                    timestamp_end=None,
                    title="Stale place",
                    summary=None,
                    latitude=None,
                    longitude=None,
                    raw_payload={
                        "googlePlaceId": "places/stale",
                        "candidateProbability": "unknown",
                    },
                    derived_payload={},
                ),
                Event(
                    source_id=timeline_source.id,
                    type="timeline_visit",
                    timestamp_start=datetime(2026, 3, 21, 12, 0, tzinfo=UTC),
                    timestamp_end=None,
                    title="Blank place",
                    summary=None,
                    latitude=None,
                    longitude=None,
                    raw_payload={"googlePlaceId": "   "},
                    derived_payload={},
                ),
                Event(
                    source_id=timeline_source.id,
                    type="timeline_activity",
                    timestamp_start=datetime(2026, 3, 21, 13, 0, tzinfo=UTC),
                    timestamp_end=None,
                    title="No place",
                    summary=None,
                    latitude=None,
                    longitude=None,
                    raw_payload={},
                    derived_payload={},
                ),
            ]
        )
        session.add_all(
            [
                Place(
                    source_id=provider_source.id,
                    external_id="places/fresh",
                    display_name="Fresh Cafe",
                    formatted_address="Berlin",
                    latitude=52.52,
                    longitude=13.405,
                    lastupdate_at=reference_now - timedelta(days=30),
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

        plan = GooglePlacesCanonicalLoader().build_plan(
            repository=PlaceRepository(session),
            provider_source_id=provider_source.id,
            refresh_max_age=timedelta(days=365 * 3),
            now=reference_now,
        )

    assert plan.scanned_event_count == 5
    assert plan.candidate_event_count == 3
    assert plan.unique_place_id_count == 2
    assert plan.fresh_cached_place_ids == ("places/fresh",)
    assert plan.place_ids_requiring_refresh == ("places/stale",)
    assert sorted(plan.cached_places_by_place_id) == ["places/fresh", "places/stale"]
    fresh_confidences = [
        candidate.confidence
        for candidate in plan.candidates_by_place_id["places/fresh"]
    ]
    stale_confidences = [
        candidate.confidence
        for candidate in plan.candidates_by_place_id["places/stale"]
    ]
    assert fresh_confidences == [
        0.9,
        0.4,
    ]
    assert stale_confidences == [None]


def test_google_places_loader_can_limit_to_top_n_place_ids() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    reference_now = datetime(2026, 3, 22, 12, 0, tzinfo=UTC)

    with Session(engine) as session:
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

        session.add_all(
            [
                Event(
                    source_id=timeline_source.id,
                    type="timeline_visit",
                    timestamp_start=datetime(2026, 3, 20, 9, 0, tzinfo=UTC),
                    timestamp_end=None,
                    title="A",
                    summary=None,
                    latitude=None,
                    longitude=None,
                    raw_payload={"googlePlaceId": "places/c"},
                    derived_payload={},
                ),
                Event(
                    source_id=timeline_source.id,
                    type="timeline_visit",
                    timestamp_start=datetime(2026, 3, 20, 10, 0, tzinfo=UTC),
                    timestamp_end=None,
                    title="B",
                    summary=None,
                    latitude=None,
                    longitude=None,
                    raw_payload={"googlePlaceId": "places/a"},
                    derived_payload={},
                ),
                Event(
                    source_id=timeline_source.id,
                    type="timeline_visit",
                    timestamp_start=datetime(2026, 3, 20, 11, 0, tzinfo=UTC),
                    timestamp_end=None,
                    title="C",
                    summary=None,
                    latitude=None,
                    longitude=None,
                    raw_payload={"googlePlaceId": "places/b"},
                    derived_payload={},
                ),
            ]
        )
        session.commit()

        plan = GooglePlacesCanonicalLoader().build_plan(
            repository=PlaceRepository(session),
            provider_source_id=provider_source.id,
            refresh_max_age=timedelta(days=365 * 3),
            max_place_ids=2,
            now=reference_now,
        )

    assert plan.scanned_event_count == 3
    assert plan.candidate_event_count == 2
    assert plan.unique_place_id_count == 2
    assert sorted(plan.candidates_by_place_id) == ["places/a", "places/b"]
    assert plan.place_ids_requiring_refresh == ("places/a", "places/b")


def test_google_places_provider_source_resolver_is_deterministic() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repository = SourceRepository(session)
        resolver = GooglePlacesProviderSourceResolver()

        created = resolver.resolve(repository=repository)
        unchanged = resolver.resolve(repository=repository)
        session.commit()

        stored_sources = session.query(Source).all()

    assert created.status == "inserted"
    assert unchanged.status == "unchanged"
    assert len(stored_sources) == 1
    assert stored_sources[0].type == "google_places_api"
    assert stored_sources[0].name == "Google Places API"
    assert stored_sources[0].external_id == "google_places_api"
    assert stored_sources[0].config == {}


def test_settings_expose_google_places_runtime_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PIXELPAST_GOOGLE_PLACES_API_KEY", "secret-key")
    monkeypatch.setenv("PIXELPAST_GOOGLE_PLACES_LANGUAGE_CODE", "de")
    monkeypatch.setenv("PIXELPAST_GOOGLE_PLACES_REGION_CODE", "DE")
    monkeypatch.setenv("PIXELPAST_GOOGLE_PLACES_REFRESH_MAX_AGE_DAYS", "730")

    settings = Settings()

    assert settings.google_places_api_key == "secret-key"
    assert settings.google_places_language_code == "de"
    assert settings.google_places_region_code == "DE"
    assert settings.google_places_refresh_max_age_days == 730
    assert settings.google_places_refresh_max_age == timedelta(days=730)


def test_google_places_client_maps_selected_snapshot_fields() -> None:
    captured: list[object] = []

    def fake_transport(request):
        captured.append(request)
        return GooglePlacesResponse(
            status_code=200,
            body=json.dumps(
                {
                    "displayName": {"text": "Cafe Central"},
                    "formattedAddress": "Mitte, Berlin",
                    "location": {"latitude": 52.52, "longitude": 13.405},
                }
            ),
        )

    client = GooglePlacesClient(
        api_key="secret-key",
        language_code="de",
        region_code="DE",
        transport=fake_transport,
    )

    snapshot = client.fetch_place(place_id="place-123")

    assert snapshot.external_id == "place-123"
    assert snapshot.display_name == "Cafe Central"
    assert snapshot.formatted_address == "Mitte, Berlin"
    assert snapshot.latitude == 52.52
    assert snapshot.longitude == 13.405
    assert len(captured) == 1
    assert captured[0].url == (
        "https://places.googleapis.com/v1/places/place-123"
        "?languageCode=de&regionCode=DE"
    )
    assert captured[0].headers["X-Goog-Api-Key"] == "secret-key"
    assert captured[0].headers["X-Goog-FieldMask"] == (
        "id,displayName,formattedAddress,location"
    )


def test_google_places_client_raises_explicit_http_error() -> None:
    client = GooglePlacesClient(
        api_key="secret-key",
        transport=lambda request: GooglePlacesResponse(
            status_code=403,
            body='{"error":{"message":"forbidden"}}',
        ),
    )

    with pytest.raises(GooglePlacesClientHttpError) as error:
        client.fetch_place(place_id="place-123")

    assert error.value.status_code == 403
    assert "forbidden" in error.value.body
    assert "forbidden" in str(error.value)


def test_google_places_client_rejects_unmappable_response_payload() -> None:
    client = GooglePlacesClient(
        api_key="secret-key",
        transport=lambda request: GooglePlacesResponse(
            status_code=200,
            body=json.dumps({"displayName": "Cafe Central"}),
        ),
    )

    with pytest.raises(GooglePlacesClientResponseError):
        client.fetch_place(place_id="place-123")


def test_google_places_client_can_refresh_place_id() -> None:
    captured: list[object] = []

    def fake_transport(request):
        captured.append(request)
        return GooglePlacesResponse(
            status_code=200,
            body=json.dumps({"id": "new-place-123"}),
        )

    client = GooglePlacesClient(
        api_key="secret-key",
        transport=fake_transport,
    )

    refreshed_id = client.refresh_place_id(place_id="places/old-place-123")

    assert refreshed_id == "places/new-place-123"
    assert len(captured) == 1
    assert captured[0].headers["X-Goog-FieldMask"] == "id"
