"""Operational lifecycle helpers for workdays-vacation ingestion runs."""

from __future__ import annotations

from pathlib import Path

from pixelpast.shared.job_run_coordinator import JobRunCoordinatorBase
from pixelpast.shared.runtime import RuntimeContext

WORKDAYS_VACATION_JOB_NAME = "workdays_vacation"
WORKDAYS_VACATION_JOB_TYPE = "ingest"
WORKDAYS_VACATION_MODE = "full"
WORKDAYS_VACATION_INITIAL_PHASE = "initializing"


class WorkdaysVacationIngestionRunCoordinator(JobRunCoordinatorBase):
    """Coordinate run bootstrap for workdays-vacation ingestion."""

    job_type = WORKDAYS_VACATION_JOB_TYPE
    job_name = WORKDAYS_VACATION_JOB_NAME
    mode = WORKDAYS_VACATION_MODE
    initial_phase = WORKDAYS_VACATION_INITIAL_PHASE

    def create_run(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
    ) -> int:
        """Persist a new workdays-vacation ingestion run."""

        return self._create_run(runtime=runtime, resolved_root=resolved_root)

    def _include_root_path_in_payload(self) -> bool:
        return True


__all__ = [
    "WORKDAYS_VACATION_INITIAL_PHASE",
    "WORKDAYS_VACATION_JOB_NAME",
    "WORKDAYS_VACATION_JOB_TYPE",
    "WORKDAYS_VACATION_MODE",
    "WorkdaysVacationIngestionRunCoordinator",
]
