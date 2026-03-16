"""Raw workbook loading for workdays-vacation ingestion."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from pixelpast.ingestion.workdays_vacation.contracts import (
    WorkdaysVacationWorkbookDescriptor,
)


@dataclass(slots=True, frozen=True)
class WorkdaysVacationWorkbookLoadProgress:
    """Represents one raw workbook load transition."""

    event: str
    workbook: WorkdaysVacationWorkbookDescriptor
    workbook_index: int
    workbook_total: int


class WorkdaysVacationWorkbookFetcher:
    """Load raw workbook bytes for discovered spreadsheet files."""

    def fetch_bytes_by_descriptor(
        self,
        *,
        workbooks: Sequence[WorkdaysVacationWorkbookDescriptor],
        on_workbook_progress: (
            Callable[[WorkdaysVacationWorkbookLoadProgress], None] | None
        ) = None,
    ) -> dict[WorkdaysVacationWorkbookDescriptor, bytes]:
        """Return raw workbook bytes indexed by workbook descriptor."""

        fetched_workbooks: dict[WorkdaysVacationWorkbookDescriptor, bytes] = {}
        workbook_total = len(workbooks)
        for index, workbook in enumerate(workbooks, start=1):
            if on_workbook_progress is not None:
                on_workbook_progress(
                    WorkdaysVacationWorkbookLoadProgress(
                        event="submitted",
                        workbook=workbook,
                        workbook_index=index,
                        workbook_total=workbook_total,
                    )
                )
            fetched_workbooks[workbook] = workbook.path.read_bytes()
            if on_workbook_progress is not None:
                on_workbook_progress(
                    WorkdaysVacationWorkbookLoadProgress(
                        event="completed",
                        workbook=workbook,
                        workbook_index=index,
                        workbook_total=workbook_total,
                    )
                )
        return fetched_workbooks


__all__ = [
    "WorkdaysVacationWorkbookFetcher",
    "WorkdaysVacationWorkbookLoadProgress",
]
