"""Calendar-specific adapters for the reusable staged ingestion runner."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from pixelpast.ingestion.calendar.connector import CalendarConnector
from pixelpast.ingestion.calendar.contracts import (
    CalendarDocumentCandidate,
    CalendarDocumentDescriptor,
    CalendarIngestionResult,
    CalendarTransformError,
)
from pixelpast.ingestion.calendar.lifecycle import CalendarIngestionRunCoordinator
from pixelpast.ingestion.calendar.persist import CalendarDocumentPersister
from pixelpast.ingestion.calendar.progress import CalendarIngestionProgressTracker
from pixelpast.persistence.repositories import EventRepository, SourceRepository
from pixelpast.shared.runtime import RuntimeContext


class CalendarIngestionPersistenceScope:
    """Wrap the calendar persistence transaction boundary for the staged runner."""

    def __init__(
        self,
        *,
        runtime: RuntimeContext,
        lifecycle: CalendarIngestionRunCoordinator,
    ) -> None:
        session = runtime.session_factory()
        self._session = session
        self._lifecycle = lifecycle
        self._persister = CalendarDocumentPersister(
            source_repository=SourceRepository(session),
            event_repository=EventRepository(session),
        )

    @property
    def persisted_source_count(self) -> int:
        return self._persister.persisted_source_count

    @property
    def persisted_event_count(self) -> int:
        return self._persister.persisted_event_count

    def count_missing_from_source(
        self,
        *,
        resolved_root: Path,
        discovered_units: Sequence[CalendarDocumentDescriptor],
    ) -> int:
        return self._lifecycle.count_missing_from_source(
            resolved_root=resolved_root,
            discovered_documents=list(discovered_units),
        )

    def persist(self, *, candidate: CalendarDocumentCandidate) -> str:
        return self._persister.persist(candidate=candidate)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

    def close(self) -> None:
        self._session.close()


class CalendarStagedIngestionStrategy:
    """Bind the calendar connector to the generic staged runner contract."""

    def __init__(self, *, connector: CalendarConnector) -> None:
        self._connector = connector
        self._seen_external_ids: set[str] = set()

    def discover_units(
        self,
        *,
        root: Path,
        on_unit_discovered,
    ) -> Sequence[CalendarDocumentDescriptor]:
        self._seen_external_ids.clear()
        return self._connector.discover_documents(
            root,
            on_document_discovered=on_unit_discovered,
        )

    def fetch_payloads(
        self,
        *,
        units: Sequence[CalendarDocumentDescriptor],
        on_batch_progress,
    ) -> dict[CalendarDocumentDescriptor, str]:
        return self._connector.fetch_text_by_descriptor(
            documents=units,
            on_document_progress=on_batch_progress,
        )

    def build_candidate(
        self,
        *,
        root: Path,
        unit: CalendarDocumentDescriptor,
        fetched_payloads: dict[CalendarDocumentDescriptor, str],
    ) -> CalendarDocumentCandidate:
        del root
        candidate = self._connector.build_document_candidate(
            document=unit,
            text=fetched_payloads[unit],
        )
        external_id = candidate.source.external_id
        if external_id is None:
            raise ValueError(
                f"Calendar document '{unit.origin_label}' is missing an external id."
            )
        if external_id in self._seen_external_ids:
            raise ValueError(
                "Duplicate calendar external id encountered within one run: "
                f"{external_id}"
            )
        self._seen_external_ids.add(external_id)
        return candidate

    def build_transform_error(
        self,
        *,
        unit: CalendarDocumentDescriptor,
        error: Exception,
    ) -> CalendarTransformError:
        return self._connector.build_transform_error(document=unit, error=error)

    def describe_unit(self, *, unit: CalendarDocumentDescriptor) -> str:
        return unit.origin_label

    def build_result(
        self,
        *,
        run_id: int,
        progress: CalendarIngestionProgressTracker,
        transform_errors: Sequence[CalendarTransformError],
    ) -> CalendarIngestionResult:
        status = "partial_failure" if transform_errors else "completed"
        counters = progress.counters
        return CalendarIngestionResult(
            run_id=run_id,
            processed_document_count=counters.persisted_document_count,
            persisted_source_count=counters.persisted_document_count,
            persisted_event_count=counters.persisted_event_count,
            error_count=len(transform_errors),
            status=status,
        )


__all__ = [
    "CalendarIngestionPersistenceScope",
    "CalendarStagedIngestionStrategy",
]
