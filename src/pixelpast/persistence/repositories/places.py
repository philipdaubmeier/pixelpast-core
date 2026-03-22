"""Repositories for derived place caching and event-place linking."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from pixelpast.persistence.models import EventPlace, Place


class PlaceUpsertResult:
    """Represents the core-field upsert outcome for one place row."""

    __slots__ = ("place", "status")

    def __init__(self, *, place: Place, status: str) -> None:
        self.place = place
        self.status = status


class EventPlaceLinkUpsertResult:
    """Represents the idempotent persistence outcome for one event-place link."""

    __slots__ = ("event_place", "status")

    def __init__(self, *, event_place: EventPlace, status: str) -> None:
        self.event_place = event_place
        self.status = status


class PlaceRepository:
    """Repository for derived place cache rows and event-place links."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_source_and_external_id(
        self,
        *,
        source_id: int,
        external_id: str,
    ) -> Place | None:
        """Return one provider-scoped place cache entry."""

        statement = select(Place).where(
            Place.source_id == source_id,
            Place.external_id == external_id,
        )
        return self._session.execute(statement).scalar_one_or_none()

    def upsert(
        self,
        *,
        source_id: int,
        external_id: str,
        display_name: str | None,
        formatted_address: str | None,
        latitude: float | None,
        longitude: float | None,
        lastupdate_at: datetime,
    ) -> PlaceUpsertResult:
        """Insert or update one provider-scoped place cache entry."""

        place = self.get_by_source_and_external_id(
            source_id=source_id,
            external_id=external_id,
        )
        if place is None:
            place = Place(
                source_id=source_id,
                external_id=external_id,
                display_name=display_name,
                formatted_address=formatted_address,
                latitude=latitude,
                longitude=longitude,
                lastupdate_at=lastupdate_at,
            )
            self._session.add(place)
            self._session.flush()
            return PlaceUpsertResult(place=place, status="inserted")

        changed = any(
            [
                place.display_name != display_name,
                place.formatted_address != formatted_address,
                place.latitude != latitude,
                place.longitude != longitude,
                place.lastupdate_at != lastupdate_at,
            ]
        )
        if changed:
            place.display_name = display_name
            place.formatted_address = formatted_address
            place.latitude = latitude
            place.longitude = longitude
            place.lastupdate_at = lastupdate_at
        self._session.flush()
        return PlaceUpsertResult(
            place=place,
            status="updated" if changed else "unchanged",
        )

    def list_event_place_links(
        self,
        *,
        event_ids: Iterable[int] | None = None,
        place_ids: Iterable[int] | None = None,
    ) -> list[EventPlace]:
        """Return deterministic event-place links filtered by event or place ids."""

        normalized_event_ids = sorted(set(event_ids or []))
        normalized_place_ids = sorted(set(place_ids or []))
        statement = select(EventPlace)
        filters = []
        if normalized_event_ids:
            filters.append(EventPlace.event_id.in_(normalized_event_ids))
        if normalized_place_ids:
            filters.append(EventPlace.place_id.in_(normalized_place_ids))
        if filters:
            statement = statement.where(*filters)
        statement = statement.order_by(EventPlace.event_id, EventPlace.place_id)
        return list(self._session.execute(statement).scalars())

    def upsert_event_place_link(
        self,
        *,
        event_id: int,
        place_id: int,
        confidence: float | None,
    ) -> EventPlaceLinkUpsertResult:
        """Insert or update one event-place association idempotently."""

        statement = select(EventPlace).where(
            EventPlace.event_id == event_id,
            EventPlace.place_id == place_id,
        )
        event_place = self._session.execute(statement).scalar_one_or_none()
        if event_place is None:
            event_place = EventPlace(
                event_id=event_id,
                place_id=place_id,
                confidence=confidence,
            )
            self._session.add(event_place)
            self._session.flush()
            return EventPlaceLinkUpsertResult(
                event_place=event_place,
                status="inserted",
            )

        if event_place.confidence == confidence:
            self._session.flush()
            return EventPlaceLinkUpsertResult(
                event_place=event_place,
                status="unchanged",
            )

        event_place.confidence = confidence
        self._session.flush()
        return EventPlaceLinkUpsertResult(
            event_place=event_place,
            status="updated",
        )
