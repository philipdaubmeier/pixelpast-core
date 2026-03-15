"""Operational lifecycle helpers for derive job runs."""

from __future__ import annotations

from pixelpast.persistence.repositories import JobRunRepository
from pixelpast.shared.progress import build_initial_job_progress_payload
from pixelpast.shared.runtime import RuntimeContext

DERIVE_JOB_TYPE = "derive"
DERIVE_INITIAL_PHASE = "initializing"


class DeriveRunCoordinator:
    """Create and bootstrap persisted run records for derive jobs."""

    def create_run(
        self,
        *,
        runtime: RuntimeContext,
        job: str,
        mode: str,
    ) -> int:
        """Persist a new derive run with a zeroed shared progress payload."""

        session = runtime.session_factory()
        try:
            job_run = JobRunRepository(session).create(
                job_type=DERIVE_JOB_TYPE,
                job=job,
                mode=mode,
                phase=DERIVE_INITIAL_PHASE,
                progress_json=build_initial_job_progress_payload(),
            )
            session.commit()
            return job_run.id
        finally:
            session.close()


__all__ = [
    "DERIVE_INITIAL_PHASE",
    "DERIVE_JOB_TYPE",
    "DeriveRunCoordinator",
]
