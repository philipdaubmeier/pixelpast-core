"""Operational lifecycle helpers for workdays-vacation ingestion runs."""

from __future__ import annotations

from pathlib import Path

from pixelpast.persistence.repositories import JobRunRepository
from pixelpast.shared.progress import build_initial_job_progress_payload
from pixelpast.shared.runtime import RuntimeContext

WORKDAYS_VACATION_JOB_NAME = "workdays_vacation"
WORKDAYS_VACATION_JOB_TYPE = "ingest"
WORKDAYS_VACATION_MODE = "full"
WORKDAYS_VACATION_INITIAL_PHASE = "initializing"


class WorkdaysVacationIngestionRunCoordinator:
    """Coordinate run bootstrap for workdays-vacation ingestion."""

    def create_run(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
    ) -> int:
        """Persist a new workdays-vacation ingestion run."""

        session = runtime.session_factory()
        try:
            job_run = JobRunRepository(session).create(
                job_type=WORKDAYS_VACATION_JOB_TYPE,
                job=WORKDAYS_VACATION_JOB_NAME,
                mode=WORKDAYS_VACATION_MODE,
                phase=WORKDAYS_VACATION_INITIAL_PHASE,
                progress_json={
                    **build_initial_job_progress_payload(),
                    "root_path": resolved_root.as_posix(),
                },
            )
            session.commit()
            return job_run.id
        finally:
            session.close()


__all__ = [
    "WORKDAYS_VACATION_INITIAL_PHASE",
    "WORKDAYS_VACATION_JOB_NAME",
    "WORKDAYS_VACATION_JOB_TYPE",
    "WORKDAYS_VACATION_MODE",
    "WorkdaysVacationIngestionRunCoordinator",
]
