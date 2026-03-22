"""Google Maps Timeline source and event persistence helpers."""

from __future__ import annotations

from pixelpast.ingestion.google_maps_timeline.contracts import (
    GoogleMapsTimelineDocumentCandidate,
)
from pixelpast.persistence.repositories import EventRepository, SourceRepository


class GoogleMapsTimelineDocumentPersister:
    """Persist one Google Maps Timeline document through canonical repositories."""

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

    def persist(self, *, candidate: GoogleMapsTimelineDocumentCandidate) -> str:
        """Persist one canonical source plus its visit/activity event set."""

        source_result = self._source_repository.upsert_by_external_id(
            external_id=_require_source_external_id(candidate),
            name=(
                candidate.source.name
                or candidate.source.external_id
                or "Google Maps Timeline"
            ),
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
                    "latitude": event.latitude,
                    "longitude": event.longitude,
                    "raw_payload": {
                        **(event.raw_payload or {}),
                        "external_event_id": event.external_event_id,
                    },
                    "derived_payload": event.derived_payload or {},
                }
                for event in candidate.events
            ],
        )
        self.persisted_source_count += 1
        self.persisted_event_count += event_result.persisted_event_count
        return _compose_document_outcome(event_result=event_result)

    def count_missing_from_source(
        self,
        *,
        candidate: GoogleMapsTimelineDocumentCandidate,
    ) -> int:
        """Preview missing events for one previously persisted export document."""

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
                    "latitude": event.latitude,
                    "longitude": event.longitude,
                    "raw_payload": {
                        **(event.raw_payload or {}),
                        "external_event_id": event.external_event_id,
                    },
                    "derived_payload": event.derived_payload or {},
                }
                for event in candidate.events
            ],
        )


def _compose_document_outcome(*, event_result) -> str:
    return (
        "inserted="
        f"{event_result.inserted_event_count};"
        "updated="
        f"{event_result.updated_event_count};"
        "unchanged="
        f"{event_result.unchanged_event_count};"
        "missing_from_source="
        f"{event_result.missing_from_source_count};"
        "skipped=0;"
        "persisted_event_count="
        f"{event_result.persisted_event_count}"
    )


def _require_source_external_id(candidate: GoogleMapsTimelineDocumentCandidate) -> str:
    if candidate.source.external_id is None:
        raise ValueError(
            "Google Maps Timeline document candidate is missing a required source "
            "external id."
        )
    return candidate.source.external_id


__all__ = ["GoogleMapsTimelineDocumentPersister"]
