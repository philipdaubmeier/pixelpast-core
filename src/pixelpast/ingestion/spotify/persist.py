"""Spotify source and event persistence helpers."""

from __future__ import annotations

from pixelpast.ingestion.spotify.contracts import SpotifyAccountCandidate
from pixelpast.persistence.repositories import EventRepository, SourceRepository
from pixelpast.shared.persistence_outcome_summary import PersistenceOutcomeSummary


class SpotifyAccountPersister:
    """Persist one Spotify account replacement set through canonical repositories."""

    def __init__(
        self,
        *,
        source_repository: SourceRepository,
        event_repository: EventRepository,
    ) -> None:
        self._source_repository = source_repository
        self._event_repository = event_repository
        self.persisted_source_count = 0
        self.persisted_event_count = 0

    def persist(self, *, candidate: SpotifyAccountCandidate) -> str:
        """Persist one Spotify account source candidate and its canonical event set."""

        source_result = self._source_repository.upsert_by_external_id(
            external_id=_require_source_external_id(candidate),
            name=candidate.source.name or candidate.source.external_id or "Spotify",
            source_type=candidate.source.type,
            config=candidate.source.config_json or {},
        )
        event_result = self._event_repository.replace_for_source(
            source_id=source_result.source.id,
            events=[
                {
                    "external_event_id": event.external_event_id,
                    "type": event.type,
                    "timestamp_start": event.timestamp_start,
                    "timestamp_end": event.timestamp_end,
                    "title": event.title,
                    "summary": event.summary,
                    "latitude": None,
                    "longitude": None,
                    "raw_payload": dict(event.raw_payload or {}),
                    "derived_payload": event.derived_payload or {},
                }
                for event in candidate.events
            ],
        )
        self.persisted_source_count += 1
        self.persisted_event_count += event_result.persisted_event_count
        return _compose_account_outcome(event_result=event_result)

    def count_missing_from_source(self, *, candidate: SpotifyAccountCandidate) -> int:
        """Preview source-scoped missing events for one Spotify account."""

        source_external_id = _require_source_external_id(candidate)
        source = self._source_repository.get_by_external_id(external_id=source_external_id)
        if source is None:
            return 0
        return self._event_repository.count_missing_from_source(
            source_id=source.id,
            events=[
                {
                    "external_event_id": event.external_event_id,
                    "type": event.type,
                    "timestamp_start": event.timestamp_start,
                    "timestamp_end": event.timestamp_end,
                    "title": event.title,
                    "summary": event.summary,
                    "latitude": None,
                    "longitude": None,
                    "raw_payload": dict(event.raw_payload or {}),
                    "derived_payload": event.derived_payload or {},
                }
                for event in candidate.events
            ],
        )


def _compose_account_outcome(*, event_result) -> str:
    return PersistenceOutcomeSummary(
        inserted=event_result.inserted_event_count,
        updated=event_result.updated_event_count,
        unchanged=event_result.unchanged_event_count,
        skipped=0,
        persisted_event_count=event_result.persisted_event_count,
    ).to_wire()


def _require_source_external_id(candidate: SpotifyAccountCandidate) -> str:
    if candidate.source.external_id is None:
        raise ValueError(
            "Spotify account candidate is missing a required source external id."
        )
    return candidate.source.external_id


__all__ = ["SpotifyAccountPersister"]
