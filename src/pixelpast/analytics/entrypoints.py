"""Derived job command entrypoints."""

import logging

from pixelpast.shared.runtime import RuntimeContext

logger = logging.getLogger(__name__)

_SUPPORTED_JOBS = frozenset({"daily-aggregate"})


def run_derive_job(*, job: str, runtime: RuntimeContext) -> None:
    """Run a stub derived-data job entrypoint."""

    if job not in _SUPPORTED_JOBS:
        available_jobs = ", ".join(sorted(_SUPPORTED_JOBS))
        raise ValueError(
            f"Unsupported job '{job}'. Available stub jobs: {available_jobs}."
        )

    logger.info(
        "derive stub executed",
        extra={
            "job": job,
            "database_url": runtime.settings.database_url,
            "status": "stub",
        },
    )
