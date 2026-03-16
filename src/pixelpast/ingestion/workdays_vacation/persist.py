"""Workdays-vacation source and event persistence helpers."""

from __future__ import annotations

from pixelpast.ingestion.workdays_vacation.contracts import (
    WorkdaysVacationWorkbookCandidate,
)
from pixelpast.persistence.repositories import EventRepository, SourceRepository


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

        source_result = self._source_repository.upsert_by_external_id(
            external_id=_require_source_external_id(candidate),
            name=(
                candidate.source.name
                or candidate.source.external_id
                or "Workdays Vacation"
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
                    "latitude": None,
                    "longitude": None,
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
        return _compose_workbook_outcome(
            event_result=event_result,
            skipped_event_count=candidate.skipped_event_count,
        )

    def count_missing_from_source(
        self,
        *,
        candidate: WorkdaysVacationWorkbookCandidate,
    ) -> int:
        """Preview source-scoped missing events for one workbook."""

        source_external_id = _require_source_external_id(candidate)
        source = self._source_repository.get_by_external_id(
            external_id=source_external_id
        )
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
                    "raw_payload": {
                        **(event.raw_payload or {}),
                        "external_event_id": event.external_event_id,
                    },
                    "derived_payload": event.derived_payload or {},
                }
                for event in candidate.events
            ],
        )


def _compose_workbook_outcome(
    *,
    event_result,
    skipped_event_count: int,
) -> str:
    return (
        "inserted="
        f"{event_result.inserted_event_count};"
        "updated="
        f"{event_result.updated_event_count};"
        "unchanged="
        f"{event_result.unchanged_event_count};"
        f"skipped={skipped_event_count};"
        "persisted_event_count="
        f"{event_result.persisted_event_count}"
    )


def _require_source_external_id(candidate: WorkdaysVacationWorkbookCandidate) -> str:
    if candidate.source.external_id is None:
        raise ValueError(
            "Workdays vacation workbook candidate is missing a required source "
            "external id."
        )
    return candidate.source.external_id


__all__ = ["WorkdaysVacationWorkbookPersister"]
