"""Tests for Google Places-derived place persistence and event-place linking."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from pixelpast.analytics.google_places import (
    GooglePlaceSnapshot,
    GooglePlacesCanonicalLoader,
    GooglePlacesPersister,
)
from pixelpast.persistence.base import Base
from pixelpast.persistence.models import Event, EventPlace, Place, Source
from pixelpast.persistence.repositories import PlaceRepository


def test_google_places_persister_handles_missing_fresh_and_stale_places() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    reference_now = datetime(2026, 3, 22, 12, 0, tzinfo=UTC)
    refreshed_at = datetime(2026, 3, 22, 12, 30, tzinfo=UTC)

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
                    timestamp_start=datetime(2026, 3, 21, 8, 0, tzinfo=UTC),
                    timestamp_end=None,
                    title="Stale visit",
                    summary=None,
                    latitude=None,
                    longitude=None,
                    raw_payload={
                        "googlePlaceId": "places/stale",
                        "candidateProbability": "0.5",
                    },
                    derived_payload={},
                ),
                Event(
                    source_id=timeline_source.id,
                    type="timeline_visit",
                    timestamp_start=datetime(2026, 3, 22, 7, 0, tzinfo=UTC),
                    timestamp_end=None,
                    title="Missing visit",
                    summary=None,
                    latitude=None,
                    longitude=None,
                    raw_payload={"googlePlaceId": "places/new"},
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

        repository = PlaceRepository(session)
        plan = GooglePlacesCanonicalLoader().build_plan(
            repository=repository,
            provider_source_id=provider_source.id,
            refresh_max_age=timedelta(days=365 * 3),
            now=reference_now,
        )

        result = GooglePlacesPersister().persist(
            repository=repository,
            provider_source_id=provider_source.id,
            plan=plan,
            fetched_places_by_place_id={
                "places/stale": GooglePlaceSnapshot(
                    external_id="places/stale",
                    display_name="Musee D'Orsay",
                    formatted_address="Paris, France",
                    latitude=48.86,
                    longitude=2.3266,
                ),
                "places/new": GooglePlaceSnapshot(
                    external_id="places/new",
                    display_name="New Bakery",
                    formatted_address="Hamburg, Germany",
                    latitude=53.5511,
                    longitude=9.9937,
                ),
            },
            refreshed_at=refreshed_at,
        )
        session.commit()

    with Session(engine) as session:
        stored_places = {
            place.external_id: place
            for place in session.query(Place).order_by(Place.external_id).all()
        }
        stored_links = [
            (link.event_id, link.place_id, link.confidence)
            for link in session.query(EventPlace)
            .order_by(EventPlace.event_id, EventPlace.place_id)
            .all()
        ]

    assert result.inserted_place_count == 1
    assert result.updated_place_count == 1
    assert result.unchanged_place_count == 1
    assert result.inserted_event_place_link_count == 3
    assert result.updated_event_place_link_count == 0
    assert result.unchanged_event_place_link_count == 0

    assert sorted(stored_places) == ["places/fresh", "places/new", "places/stale"]
    assert stored_places["places/fresh"].display_name == "Fresh Cafe"
    assert stored_places["places/fresh"].lastupdate_at == (
        reference_now - timedelta(days=10)
    )
    assert stored_places["places/stale"].display_name == "Musee D'Orsay"
    assert stored_places["places/stale"].formatted_address == "Paris, France"
    assert stored_places["places/stale"].latitude == 48.86
    assert stored_places["places/stale"].longitude == 2.3266
    assert stored_places["places/stale"].lastupdate_at == refreshed_at
    assert stored_places["places/new"].display_name == "New Bakery"
    assert stored_places["places/new"].formatted_address == "Hamburg, Germany"
    assert stored_places["places/new"].lastupdate_at == refreshed_at
    assert len(stored_links) == 3


def test_google_places_persister_reconciles_conflicting_event_links() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    reference_now = datetime(2026, 3, 22, 12, 0, tzinfo=UTC)
    refreshed_at = datetime(2026, 3, 22, 12, 45, tzinfo=UTC)

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

        event = Event(
            source_id=timeline_source.id,
            type="timeline_visit",
            timestamp_start=datetime(2026, 3, 21, 8, 0, tzinfo=UTC),
            timestamp_end=None,
            title="Visit",
            summary=None,
            latitude=None,
            longitude=None,
            raw_payload={
                "googlePlaceId": "places/current",
                "candidateProbability": 0.61,
            },
            derived_payload={},
        )
        session.add(event)
        session.flush()

        old_place = Place(
            source_id=provider_source.id,
            external_id="places/old",
            display_name="Old Place",
            formatted_address="Old address",
            latitude=1.0,
            longitude=2.0,
            lastupdate_at=reference_now - timedelta(days=20),
        )
        current_place = Place(
            source_id=provider_source.id,
            external_id="places/current",
            display_name="Current Place",
            formatted_address="Current address",
            latitude=3.0,
            longitude=4.0,
            lastupdate_at=reference_now - timedelta(days=5),
        )
        session.add_all([old_place, current_place])
        session.flush()
        session.add_all(
            [
                EventPlace(
                    event_id=event.id,
                    place_id=old_place.id,
                    confidence=0.2,
                ),
                EventPlace(
                    event_id=event.id,
                    place_id=current_place.id,
                    confidence=0.2,
                ),
            ]
        )
        session.commit()

        repository = PlaceRepository(session)
        plan = GooglePlacesCanonicalLoader().build_plan(
            repository=repository,
            provider_source_id=provider_source.id,
            refresh_max_age=timedelta(days=365 * 3),
            now=reference_now,
        )

        result = GooglePlacesPersister().persist(
            repository=repository,
            provider_source_id=provider_source.id,
            plan=plan,
            fetched_places_by_place_id={},
            refreshed_at=refreshed_at,
        )
        session.commit()
        current_place_id = current_place.id
        event_id = event.id

    with Session(engine) as session:
        stored_links = session.query(EventPlace).order_by(EventPlace.place_id).all()

    assert result.inserted_place_count == 0
    assert result.updated_place_count == 0
    assert result.unchanged_place_count == 1
    assert result.inserted_event_place_link_count == 0
    assert result.updated_event_place_link_count == 1
    assert result.unchanged_event_place_link_count == 0
    assert [(link.event_id, link.place_id, link.confidence) for link in stored_links] == [
        (event_id, current_place_id, 0.61)
    ]


def test_google_places_persister_counts_stale_refresh_without_data_changes_as_unchanged() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    reference_now = datetime(2026, 3, 22, 12, 0, tzinfo=UTC)
    refreshed_at = datetime(2026, 3, 22, 12, 45, tzinfo=UTC)

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

        session.add(
            Event(
                source_id=timeline_source.id,
                type="timeline_visit",
                timestamp_start=datetime(2026, 3, 21, 8, 0, tzinfo=UTC),
                timestamp_end=None,
                title="Visit",
                summary=None,
                latitude=None,
                longitude=None,
                raw_payload={"googlePlaceId": "places/stale"},
                derived_payload={},
            )
        )
        session.add(
            Place(
                source_id=provider_source.id,
                external_id="places/stale",
                display_name="Museum",
                formatted_address="Paris",
                latitude=48.8566,
                longitude=2.3522,
                lastupdate_at=reference_now - timedelta(days=1200),
            )
        )
        session.commit()

        repository = PlaceRepository(session)
        plan = GooglePlacesCanonicalLoader().build_plan(
            repository=repository,
            provider_source_id=provider_source.id,
            refresh_max_age=timedelta(days=365 * 3),
            now=reference_now,
        )

        result = GooglePlacesPersister().persist(
            repository=repository,
            provider_source_id=provider_source.id,
            plan=plan,
            fetched_places_by_place_id={
                "places/stale": GooglePlaceSnapshot(
                    external_id="places/stale",
                    display_name="Museum",
                    formatted_address="Paris",
                    latitude=48.8566,
                    longitude=2.3522,
                )
            },
            refreshed_at=refreshed_at,
        )
        session.commit()

    with Session(engine) as session:
        stored_place = session.query(Place).one()

    assert result.inserted_place_count == 0
    assert result.updated_place_count == 0
    assert result.unchanged_place_count == 1
    assert stored_place.lastupdate_at == refreshed_at
