"""Operational lifecycle helpers for calendar ingestion runs."""

from __future__ import annotations

from pathlib import Path

from pixelpast.persistence.repositories import JobRunRepository
from pixelpast.shared.progress import build_initial_job_progress_payload
from pixelpast.shared.runtime import RuntimeContext

CALENDAR_JOB_NAME = "calendar"
CALENDAR_JOB_TYPE = "ingest"
CALENDAR_MODE = "full"
CALENDAR_INITIAL_PHASE = "initializing"


class CalendarIngestionRunCoordinator:
    """Coordinate run bootstrap for calendar ingestion."""

    def create_run(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
    ) -> int:
        """Persist a new calendar ingestion run."""

        session = runtime.session_factory()
        try:
            job_run = JobRunRepository(session).create(
                job_type=CALENDAR_JOB_TYPE,
                job=CALENDAR_JOB_NAME,
                mode=CALENDAR_MODE,
                phase=CALENDAR_INITIAL_PHASE,
                progress_json={
                    **build_initial_job_progress_payload(),
                    "root_path": resolved_root.as_posix(),
                },
            )
            session.commit()
            return job_run.id
        finally:
            session.close()

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
