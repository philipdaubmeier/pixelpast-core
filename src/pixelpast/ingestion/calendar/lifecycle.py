"""Operational lifecycle helpers for calendar ingestion runs."""

from __future__ import annotations

from pathlib import Path

from pixelpast.shared.job_run_coordinator import JobRunCoordinatorBase
from pixelpast.shared.runtime import RuntimeContext

CALENDAR_JOB_NAME = "calendar"
CALENDAR_JOB_TYPE = "ingest"
CALENDAR_MODE = "full"
CALENDAR_INITIAL_PHASE = "initializing"


class CalendarIngestionRunCoordinator(JobRunCoordinatorBase):
    """Coordinate run bootstrap for calendar ingestion."""

    job_type = CALENDAR_JOB_TYPE
    job_name = CALENDAR_JOB_NAME
    mode = CALENDAR_MODE
    initial_phase = CALENDAR_INITIAL_PHASE

    def create_run(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
    ) -> int:
        """Persist a new calendar ingestion run."""

        return self._create_run(runtime=runtime, resolved_root=resolved_root)

    def _include_root_path_in_payload(self) -> bool:
        return True

    def count_missing_from_source(
        self,
        *,
        resolved_root: Path,
        discovered_documents: list[object],
    ) -> int:
        """Return the explicit v1 missing-from-source count for calendar ingestion."""

        del resolved_root, discovered_documents
        return 0


__all__ = [
    "CALENDAR_INITIAL_PHASE",
    "CALENDAR_JOB_NAME",
    "CALENDAR_JOB_TYPE",
    "CALENDAR_MODE",
    "CalendarIngestionRunCoordinator",
]
