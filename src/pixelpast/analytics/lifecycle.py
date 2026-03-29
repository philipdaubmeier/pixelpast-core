"""Operational lifecycle helpers for derive job runs."""

from __future__ import annotations

from pixelpast.shared.runtime import RuntimeContext
from pixelpast.shared.job_run_coordinator import JobRunCoordinatorBase

DERIVE_JOB_TYPE = "derive"
DERIVE_INITIAL_PHASE = "initializing"


class DeriveRunCoordinator(JobRunCoordinatorBase):
    """Create and bootstrap persisted run records for derive jobs."""

    job_type = DERIVE_JOB_TYPE
    job_name = "derive"
    mode = "full"
    initial_phase = DERIVE_INITIAL_PHASE

    def create_run(
        self,
        *,
        runtime: RuntimeContext,
        job: str,
        mode: str,
    ) -> int:
        """Persist a new derive run with a zeroed shared progress payload."""

        return self._create_run(runtime=runtime, job_name=job, mode=mode)


__all__ = [
    "DERIVE_INITIAL_PHASE",
    "DERIVE_JOB_TYPE",
    "DeriveRunCoordinator",
]
