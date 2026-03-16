"""Workdays-vacation-specific adapters for the reusable staged ingestion runner."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from pixelpast.ingestion.workdays_vacation.connector import WorkdaysVacationConnector
from pixelpast.ingestion.workdays_vacation.contracts import (
    WorkdaysVacationIngestionResult,
    WorkdaysVacationTransformError,
    WorkdaysVacationWorkbookCandidate,
    WorkdaysVacationWorkbookDescriptor,
)
from pixelpast.ingestion.workdays_vacation.lifecycle import (
    WorkdaysVacationIngestionRunCoordinator,
)
from pixelpast.ingestion.workdays_vacation.persist import (
    WorkdaysVacationWorkbookPersister,
)
from pixelpast.ingestion.workdays_vacation.progress import (
    WorkdaysVacationIngestionProgressTracker,
)
from pixelpast.persistence.repositories import EventRepository, SourceRepository
from pixelpast.shared.runtime import RuntimeContext


class WorkdaysVacationIngestionPersistenceScope:
    """Wrap the workdays-vacation persistence transaction boundary."""

    def __init__(
        self,
        *,
        runtime: RuntimeContext,
        lifecycle: WorkdaysVacationIngestionRunCoordinator,
    ) -> None:
        del lifecycle
        session = runtime.session_factory()
        self._session = session
        self._persister = WorkdaysVacationWorkbookPersister(
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
        discovered_units: Sequence[WorkdaysVacationWorkbookDescriptor],
        candidates: Sequence[WorkdaysVacationWorkbookCandidate],
    ) -> int:
        del resolved_root, discovered_units
        return sum(
            self._persister.count_missing_from_source(candidate=candidate)
            for candidate in candidates
        )

    def persist(self, *, candidate: WorkdaysVacationWorkbookCandidate) -> str:
        return self._persister.persist(candidate=candidate)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

    def close(self) -> None:
        self._session.close()


class WorkdaysVacationStagedIngestionStrategy:
    """Bind the workbook connector to the generic staged runner contract."""

    def __init__(self, *, connector: WorkdaysVacationConnector) -> None:
        self._connector = connector

    def discover_units(
        self,
        *,
        root: Path,
        on_unit_discovered,
    ) -> Sequence[WorkdaysVacationWorkbookDescriptor]:
        return self._connector.discover_workbooks(
            root,
            on_workbook_discovered=on_unit_discovered,
        )

    def fetch_payloads(
        self,
        *,
        units: Sequence[WorkdaysVacationWorkbookDescriptor],
        on_batch_progress,
    ) -> dict[WorkdaysVacationWorkbookDescriptor, bytes]:
        return self._connector.fetch_bytes_by_descriptor(
            workbooks=units,
            on_workbook_progress=on_batch_progress,
        )

    def build_candidate(
        self,
        *,
        root: Path,
        unit: WorkdaysVacationWorkbookDescriptor,
        fetched_payloads: dict[WorkdaysVacationWorkbookDescriptor, bytes],
    ) -> WorkdaysVacationWorkbookCandidate:
        del root
        return self._connector.build_workbook_candidate(
            workbook=unit,
            payload=fetched_payloads[unit],
        )

    def build_transform_error(
        self,
        *,
        unit: WorkdaysVacationWorkbookDescriptor,
        error: Exception,
    ) -> WorkdaysVacationTransformError:
        return self._connector.build_transform_error(workbook=unit, error=error)

    def describe_unit(self, *, unit: WorkdaysVacationWorkbookDescriptor) -> str:
        return unit.origin_label

    def build_result(
        self,
        *,
        run_id: int,
        progress: WorkdaysVacationIngestionProgressTracker,
        transform_errors: Sequence[WorkdaysVacationTransformError],
    ) -> WorkdaysVacationIngestionResult:
        status = "partial_failure" if transform_errors else "completed"
        counters = progress.counters
        return WorkdaysVacationIngestionResult(
            run_id=run_id,
            processed_workbook_count=counters.persisted_workbook_count,
            persisted_source_count=counters.persisted_workbook_count,
            persisted_event_count=counters.persisted_event_count,
            error_count=len(transform_errors),
            status=status,
        )


__all__ = [
    "WorkdaysVacationIngestionPersistenceScope",
    "WorkdaysVacationStagedIngestionStrategy",
]
