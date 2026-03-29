"""Workdays-vacation source and event persistence helpers."""

from __future__ import annotations

from pixelpast.ingestion.workdays_vacation.contracts import (
    WorkdaysVacationWorkbookCandidate,
)
from pixelpast.ingestion.persister_helpers import (
    compose_event_persistence_outcome,
    count_missing_events_for_source,
    replace_events_for_source,
    upsert_required_source,
)
from pixelpast.persistence.repositories import EventRepository, SourceRepository

_MISSING_EXTERNAL_ID_MESSAGE = (
    "Workdays vacation workbook candidate is missing a required source external id."
)


class WorkdaysVacationWorkbookPersister:
    """Persist one workbook through canonical repositories."""

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

    def persist(self, *, candidate: WorkdaysVacationWorkbookCandidate) -> str:
        """Persist one workbook source candidate and its canonical event set."""

        event_payloads = _build_event_payloads(candidate=candidate)
        source_id = upsert_required_source(
            source_repository=self._source_repository,
            source=candidate.source,
            default_name="Workdays Vacation",
            missing_external_id_message=_MISSING_EXTERNAL_ID_MESSAGE,
        )
        event_result = replace_events_for_source(
            event_repository=self._event_repository,
            source_id=source_id,
            event_payloads=event_payloads,
        )
        self.persisted_source_count += 1
        self.persisted_event_count += event_result.persisted_event_count
        return compose_event_persistence_outcome(
            event_result=event_result,
            skipped_event_count=candidate.skipped_event_count,
        )

    def count_missing_from_source(
        self,
        *,
        candidate: WorkdaysVacationWorkbookCandidate,
    ) -> int:
        """Preview source-scoped missing events for one workbook."""

        return count_missing_events_for_source(
            source_repository=self._source_repository,
            event_repository=self._event_repository,
            source=candidate.source,
            event_payloads=_build_event_payloads(candidate=candidate),
            missing_external_id_message=_MISSING_EXTERNAL_ID_MESSAGE,
        )


def _build_event_payloads(
    *,
    candidate: WorkdaysVacationWorkbookCandidate,
) -> list[dict[str, object]]:
    return [
        {
            "external_event_id": event.external_event_id,
            "type": event.type,
            "timestamp_start": event.timestamp_start,
            "timestamp_end": event.timestamp_end,
            "title": event.title,
            "summary": event.summary,
            "latitude": None,
            "longitude": None,
            "raw_payload": {
                **(event.raw_payload or {}),
                "external_event_id": event.external_event_id,
            },
            "derived_payload": event.derived_payload or {},
        }
        for event in candidate.events
    ]


__all__ = ["WorkdaysVacationWorkbookPersister"]
