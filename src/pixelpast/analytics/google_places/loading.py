"""Canonical input loading and refresh planning for Google Places derivation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from pixelpast.persistence.models import Place
from pixelpast.persistence.repositories import (
    GooglePlaceEventCandidateLoadResult,
    GooglePlaceEventCandidateSnapshot,
    PlaceRepository,
)


@dataclass(slots=True, frozen=True)
class GooglePlacesResolvePlan:
    """Deterministic planning result for one Google Places derive pass."""

    scanned_event_count: int
    candidate_event_count: int
    unique_place_id_count: int
    candidate_events: tuple[GooglePlaceEventCandidateSnapshot, ...]
    candidates_by_place_id: dict[str, tuple[GooglePlaceEventCandidateSnapshot, ...]]
    cached_places_by_place_id: dict[str, Place]
    fresh_cached_place_ids: tuple[str, ...]
    place_ids_requiring_refresh: tuple[str, ...]


class GooglePlacesCanonicalLoader:
    """Load canonical Google place inputs and plan cache-aware refresh work."""

    def load_candidates(
        self,
        *,
        repository: PlaceRepository,
    ) -> GooglePlaceEventCandidateLoadResult:
        """Return canonical events carrying a Google place identifier."""

        return repository.load_google_place_event_candidates()

    def build_plan(
        self,
        *,
        repository: PlaceRepository,
        provider_source_id: int,
        refresh_max_age: timedelta,
        now: datetime | None = None,
    ) -> GooglePlacesResolvePlan:
        """Return deduplicated place ids split into fresh and refresh-required sets."""

        load_result = self.load_candidates(repository=repository)
        candidate_events = tuple(load_result.candidate_events)
        place_ids = sorted(
            {candidate.google_place_id for candidate in candidate_events}
        )
        cached_places = repository.list_by_source_and_external_ids(
            source_id=provider_source_id,
            external_ids=place_ids,
        )
        cached_places_by_place_id = {
            place.external_id: place for place in cached_places
        }
        refresh_cutoff = (now or datetime.now(UTC)) - refresh_max_age

        candidates_by_place_id: dict[str, list[GooglePlaceEventCandidateSnapshot]] = {}
        for candidate in candidate_events:
            candidates_by_place_id.setdefault(candidate.google_place_id, []).append(
                candidate
            )

        fresh_cached_place_ids: list[str] = []
        place_ids_requiring_refresh: list[str] = []
        for place_id in place_ids:
            cached_place = cached_places_by_place_id.get(place_id)
            if (
                cached_place is not None
                and cached_place.lastupdate_at >= refresh_cutoff
            ):
                fresh_cached_place_ids.append(place_id)
                continue
            place_ids_requiring_refresh.append(place_id)

        return GooglePlacesResolvePlan(
            scanned_event_count=load_result.scanned_event_count,
            candidate_event_count=len(candidate_events),
            unique_place_id_count=len(place_ids),
            candidate_events=candidate_events,
            candidates_by_place_id={
                place_id: tuple(candidates_by_place_id[place_id])
                for place_id in sorted(candidates_by_place_id)
            },
            cached_places_by_place_id=cached_places_by_place_id,
            fresh_cached_place_ids=tuple(fresh_cached_place_ids),
            place_ids_requiring_refresh=tuple(place_ids_requiring_refresh),
        )
