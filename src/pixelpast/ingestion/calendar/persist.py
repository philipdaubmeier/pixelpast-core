"""Calendar source and event persistence helpers."""

from __future__ import annotations

from pixelpast.ingestion.calendar.contracts import CalendarDocumentCandidate
from pixelpast.persistence.repositories import EventRepository, SourceRepository


class CalendarDocumentPersister:
    """Persist one calendar document through canonical repositories."""

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

    def persist(self, *, candidate: CalendarDocumentCandidate) -> str:
        """Persist one calendar source candidate and its canonical event set."""

        source_result = self._source_repository.upsert_by_external_id(
            external_id=_require_source_external_id(candidate),
            name=candidate.source.name or candidate.source.external_id or "Calendar",
            source_type=candidate.source.type,
            config=candidate.source.config_json or {},
        )
        event_result = self._event_repository.replace_for_source(
            source_id=source_result.source.id,
            events=[
                {
                    "type": event.type,
                    "timestamp_start": event.timestamp_start,
                    "timestamp_end": event.timestamp_end,
                    "title": event.title,
                    "summary": event.summary,
                    "latitude": None,
                    "longitude": None,
                    "raw_payload": event.raw_payload or {},
                    "derived_payload": event.derived_payload or {},
                }
                for event in candidate.events
            ],
        )
        self.persisted_source_count += 1
        self.persisted_event_count += event_result.persisted_event_count
        return _compose_document_outcome(
            source_status=source_result.status,
            event_status=event_result.status,
            event_count=event_result.persisted_event_count,
        )


def _compose_document_outcome(
    *,
    source_status: str,
    event_status: str,
    event_count: int,
) -> str:
    if source_status == "inserted":
        return f"inserted:{event_count}"
    if source_status == "updated" or event_status in {"inserted", "updated"}:
        return f"updated:{event_count}"
    return f"unchanged:{event_count}"


def _require_source_external_id(candidate: CalendarDocumentCandidate) -> str:
    if candidate.source.external_id is None:
        raise ValueError(
            "Calendar document candidate is missing a required source external id."
        )
    return candidate.source.external_id


__all__ = ["CalendarDocumentPersister"]
