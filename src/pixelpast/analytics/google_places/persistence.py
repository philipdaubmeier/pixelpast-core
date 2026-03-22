"""Persistence orchestration for Google Places-derived place resolution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pixelpast.analytics.google_places.client import GooglePlaceSnapshot
from pixelpast.analytics.google_places.loading import GooglePlacesResolvePlan
from pixelpast.persistence.models import Place
from pixelpast.persistence.repositories import PlaceRepository


@dataclass(slots=True, frozen=True)
class GooglePlacesPersistenceResult:
    """Explicit persistence counters for place cache and event-place links."""

    inserted_place_count: int
    updated_place_count: int
    unchanged_place_count: int
    inserted_event_place_link_count: int
    updated_event_place_link_count: int
    unchanged_event_place_link_count: int


class GooglePlacesPersister:
    """Persist resolved place snapshots and reconcile event-place links."""

    def persist(
        self,
        *,
        repository: PlaceRepository,
        provider_source_id: int,
        plan: GooglePlacesResolvePlan,
        fetched_places_by_place_id: dict[str, GooglePlaceSnapshot],
        refreshed_at: datetime,
    ) -> GooglePlacesPersistenceResult:
        """Persist fetched place snapshots and idempotent event-place links."""

        missing_place_ids = sorted(
            set(plan.place_ids_requiring_refresh) - set(fetched_places_by_place_id)
        )
        if missing_place_ids:
            missing_ids = ", ".join(missing_place_ids)
            raise ValueError(
                "Fetched place snapshots are missing required place ids: "
                f"{missing_ids}."
            )

        resolved_places_by_place_id: dict[str, Place] = {}
        inserted_place_count = 0
        updated_place_count = 0
        unchanged_place_count = 0

        for place_id in plan.fresh_cached_place_ids:
            cached_place = plan.cached_places_by_place_id.get(place_id)
            if cached_place is None:
                raise ValueError(
                    "Google Places refresh plan marked a place id as fresh without "
                    f"a cached row: {place_id}."
                )
            resolved_places_by_place_id[place_id] = cached_place
            unchanged_place_count += 1

        for place_id in plan.place_ids_requiring_refresh:
            snapshot = fetched_places_by_place_id[place_id]
            upsert_result = repository.upsert(
                source_id=provider_source_id,
                external_id=snapshot.external_id,
                display_name=snapshot.display_name,
                formatted_address=snapshot.formatted_address,
                latitude=snapshot.latitude,
                longitude=snapshot.longitude,
                lastupdate_at=refreshed_at,
            )
            resolved_places_by_place_id[place_id] = upsert_result.place
            if upsert_result.status == "inserted":
                inserted_place_count += 1
            elif upsert_result.status == "updated":
                updated_place_count += 1
            else:
                unchanged_place_count += 1

        inserted_event_place_link_count = 0
        updated_event_place_link_count = 0
        unchanged_event_place_link_count = 0

        for candidate in plan.candidate_events:
            place = resolved_places_by_place_id.get(candidate.google_place_id)
            if place is None:
                raise ValueError(
                    "Google Places persistence could not resolve place id "
                    f"{candidate.google_place_id} for event {candidate.event_id}."
                )
            link_result = repository.reconcile_event_place_link(
                event_id=candidate.event_id,
                place_id=place.id,
                confidence=candidate.confidence,
            )
            if link_result.status == "inserted":
                inserted_event_place_link_count += 1
            elif link_result.status == "updated":
                updated_event_place_link_count += 1
            else:
                unchanged_event_place_link_count += 1

        return GooglePlacesPersistenceResult(
            inserted_place_count=inserted_place_count,
            updated_place_count=updated_place_count,
            unchanged_place_count=unchanged_place_count,
            inserted_event_place_link_count=inserted_event_place_link_count,
            updated_event_place_link_count=updated_event_place_link_count,
            unchanged_event_place_link_count=unchanged_event_place_link_count,
        )
