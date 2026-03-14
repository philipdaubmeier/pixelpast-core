"""Derived job command entrypoints."""

import logging
from datetime import date

from pixelpast.analytics.daily_aggregate import DailyAggregateJob
from pixelpast.shared.runtime import RuntimeContext

logger = logging.getLogger(__name__)

_SUPPORTED_JOBS = frozenset({"daily-aggregate"})


def list_supported_derive_jobs() -> tuple[str, ...]:
    """Return the supported derive job names in deterministic order."""

    return tuple(sorted(_SUPPORTED_JOBS))


def run_derive_job(
    *,
    job: str,
    runtime: RuntimeContext,
    start_date: date | None = None,
    end_date: date | None = None,
) -> None:
    """Run a derived-data job entrypoint."""

    if job not in _SUPPORTED_JOBS:
        available_jobs = ", ".join(list_supported_derive_jobs())
        raise ValueError(
            f"Unsupported job '{job}'. Available jobs: {available_jobs}."
        )

    if job == "daily-aggregate":
        result = DailyAggregateJob().run(
            runtime=runtime,
            start_date=start_date,
            end_date=end_date,
        )
        logger.info(
            "derive completed",
            extra={
                "job": job,
                "database_url": runtime.settings.database_url,
                "mode": result.mode,
                "start_date": result.start_date.isoformat()
                if result.start_date is not None
                else None,
                "end_date": result.end_date.isoformat()
                if result.end_date is not None
                else None,
                "aggregate_count": result.aggregate_count,
                "total_events": result.total_events,
                "media_count": result.media_count,
            },
        )
        return

    raise AssertionError(f"Unhandled derive job: {job}")
