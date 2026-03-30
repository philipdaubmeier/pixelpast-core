"""Derived job command entrypoints."""

import logging
from collections.abc import Callable
from datetime import date

from pixelpast.analytics.asset_thumbnails import (
    ASSET_THUMBNAILS_JOB_NAME,
    AssetThumbnailJob,
    AssetThumbnailJobResult,
)
from pixelpast.analytics.daily_aggregate import DailyAggregateJob
from pixelpast.analytics.daily_aggregate.job import DailyAggregateJobResult
from pixelpast.analytics.google_places import GooglePlacesJob, GooglePlacesJobResult
from pixelpast.shared.progress import JobProgressSnapshot
from pixelpast.shared.runtime import RuntimeContext

logger = logging.getLogger(__name__)

_SUPPORTED_JOBS = frozenset(
    {ASSET_THUMBNAILS_JOB_NAME, "daily-aggregate", "google_places"}
)


def list_supported_derive_jobs() -> tuple[str, ...]:
    """Return the supported derive job names in deterministic order."""

    return tuple(sorted(_SUPPORTED_JOBS))


def run_derive_job(
    *,
    job: str,
    runtime: RuntimeContext,
    start_date: date | None = None,
    end_date: date | None = None,
    max_place_ids: int | None = None,
    renditions: tuple[str, ...] = (),
    force: bool = False,
    progress_callback: Callable[[JobProgressSnapshot], None] | None = None,
) -> DailyAggregateJobResult | GooglePlacesJobResult | AssetThumbnailJobResult:
    """Run a derived-data job entrypoint."""

    if job not in _SUPPORTED_JOBS:
        available_jobs = ", ".join(list_supported_derive_jobs())
        raise ValueError(
            f"Unsupported job '{job}'. Available jobs: {available_jobs}."
        )

    if job == ASSET_THUMBNAILS_JOB_NAME:
        if start_date is not None or end_date is not None:
            raise ValueError(
                "Asset thumbnail derivation does not support --start-date/--end-date."
            )
        if max_place_ids is not None:
            raise ValueError(
                "Asset thumbnail derivation does not support --top-place-ids."
            )

        result = AssetThumbnailJob().run(
            runtime=runtime,
            renditions=renditions,
            force=force,
            progress_callback=progress_callback,
        )
        logger.info(
            "derive completed",
            extra={
                "job": job,
                "database_url": runtime.settings.database_url,
                "run_id": result.run_id,
                "mode": result.mode,
                "status": result.status,
                "asset_count": result.asset_count,
                "rendition_count": result.rendition_count,
                "generated_count": result.generated_count,
                "overwritten_count": result.overwritten_count,
                "unchanged_count": result.unchanged_count,
                "skipped_count": result.skipped_count,
                "failed_count": result.failed_count,
            },
        )
        return result

    if job == "daily-aggregate":
        if renditions:
            raise ValueError(
                "Daily aggregate derivation does not support --rendition."
            )
        if force:
            raise ValueError("Daily aggregate derivation does not support --force.")
        result = DailyAggregateJob().run(
            runtime=runtime,
            start_date=start_date,
            end_date=end_date,
            progress_callback=progress_callback,
        )
        logger.info(
            "derive completed",
            extra={
                "job": job,
                "database_url": runtime.settings.database_url,
                "run_id": result.run_id,
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
        return result

    if job == "google_places":
        if renditions:
            raise ValueError("Google Places derivation does not support --rendition.")
        if force:
            raise ValueError("Google Places derivation does not support --force.")
        result = GooglePlacesJob().run(
            runtime=runtime,
            start_date=start_date,
            end_date=end_date,
            max_place_ids=max_place_ids,
            progress_callback=progress_callback,
        )
        logger.info(
            "derive completed",
            extra={
                "job": job,
                "database_url": runtime.settings.database_url,
                "run_id": result.run_id,
                "mode": result.mode,
                "status": result.status,
                "scanned_event_count": result.scanned_event_count,
                "qualifying_event_count": result.qualifying_event_count,
                "unique_place_id_count": result.unique_place_id_count,
                "remote_fetch_count": result.remote_fetch_count,
                "cached_reuse_count": result.cached_reuse_count,
                "inserted_place_count": result.inserted_place_count,
                "updated_place_count": result.updated_place_count,
                "unchanged_place_count": result.unchanged_place_count,
                "inserted_event_place_link_count": (
                    result.inserted_event_place_link_count
                ),
                "updated_event_place_link_count": (
                    result.updated_event_place_link_count
                ),
                "unchanged_event_place_link_count": (
                    result.unchanged_event_place_link_count
                ),
            },
        )
        return result

    raise AssertionError(f"Unhandled derive job: {job}")
