"""Composition facade for workdays-vacation discovery, fetch, and transform."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from pixelpast.ingestion.workdays_vacation.contracts import (
    WorkdaysVacationTransformError,
    WorkdaysVacationWorkbookCandidate,
    WorkdaysVacationWorkbookDescriptor,
)
from pixelpast.ingestion.workdays_vacation.discovery import (
    WorkdaysVacationWorkbookDiscoverer,
)
from pixelpast.ingestion.workdays_vacation.fetch import (
    WorkdaysVacationWorkbookFetcher,
    WorkdaysVacationWorkbookLoadProgress,
)
from pixelpast.ingestion.workdays_vacation.transform import (
    build_workdays_vacation_event_candidates,
    build_workdays_vacation_source_candidate,
    parse_workdays_vacation_workbook,
)


class WorkdaysVacationConnector:
    """Facade that composes workbook discovery, fetch, and transform stages."""

    def __init__(
        self,
        *,
        workbook_discoverer: WorkdaysVacationWorkbookDiscoverer | None = None,
        workbook_fetcher: WorkdaysVacationWorkbookFetcher | None = None,
    ) -> None:
        self._workbook_discoverer = (
            workbook_discoverer
            if workbook_discoverer is not None
            else WorkdaysVacationWorkbookDiscoverer()
        )
        self._workbook_fetcher = (
            workbook_fetcher
            if workbook_fetcher is not None
            else WorkdaysVacationWorkbookFetcher()
        )

    def discover_workbooks(
        self,
        root: Path,
        *,
        on_workbook_discovered: (
            Callable[[WorkdaysVacationWorkbookDescriptor, int], None] | None
        ) = None,
    ) -> list[WorkdaysVacationWorkbookDescriptor]:
        """Delegate workbook discovery to the dedicated discoverer component."""

        return self._workbook_discoverer.discover_workbooks(
            root,
            on_workbook_discovered=on_workbook_discovered,
        )

    def fetch_bytes_by_descriptor(
        self,
        *,
        workbooks: Sequence[WorkdaysVacationWorkbookDescriptor],
        on_workbook_progress: (
            Callable[[WorkdaysVacationWorkbookLoadProgress], None] | None
        ) = None,
    ) -> dict[WorkdaysVacationWorkbookDescriptor, bytes]:
        """Load raw workbook bytes for the discovered workbook set."""

        return self._workbook_fetcher.fetch_bytes_by_descriptor(
            workbooks=workbooks,
            on_workbook_progress=on_workbook_progress,
        )

    def build_workbook_candidate(
        self,
        *,
        workbook: WorkdaysVacationWorkbookDescriptor,
        payload: bytes,
    ) -> WorkdaysVacationWorkbookCandidate:
        """Build one persistable workbook candidate."""

        parsed_workbook = parse_workdays_vacation_workbook(
            descriptor=workbook,
            payload=payload,
        )
        return WorkdaysVacationWorkbookCandidate(
            workbook=workbook,
            source=build_workdays_vacation_source_candidate(parsed_workbook),
            events=build_workdays_vacation_event_candidates(parsed_workbook),
            skipped_event_count=len(parsed_workbook.skipped_day_warnings),
        )

    def build_transform_error(
        self,
        *,
        workbook: WorkdaysVacationWorkbookDescriptor,
        error: Exception,
    ) -> WorkdaysVacationTransformError:
        """Translate one transform failure into the stable error contract."""

        return WorkdaysVacationTransformError(workbook=workbook, message=str(error))


__all__ = ["WorkdaysVacationConnector"]
