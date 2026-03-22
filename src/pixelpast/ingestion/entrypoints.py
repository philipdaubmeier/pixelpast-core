"""Ingestion command entrypoints."""

import logging
from collections.abc import Callable

from pixelpast.ingestion.calendar.service import (
    CalendarIngestionResult,
    CalendarIngestionService,
)
from pixelpast.ingestion.google_maps_timeline.service import (
    GoogleMapsTimelineIngestionResult,
    GoogleMapsTimelineIngestionService,
)
from pixelpast.ingestion.photos.service import (
    PhotoIngestionResult,
    PhotoIngestionService,
)
from pixelpast.ingestion.spotify.service import (
    SpotifyIngestionResult,
    SpotifyIngestionService,
)
from pixelpast.ingestion.workdays_vacation.service import (
    WorkdaysVacationIngestionResult,
    WorkdaysVacationIngestionService,
)
from pixelpast.shared.progress import JobProgressSnapshot
from pixelpast.shared.runtime import RuntimeContext

logger = logging.getLogger(__name__)

_SUPPORTED_SOURCES = frozenset(
    {
        "calendar",
        "google_maps_timeline",
        "photos",
        "spotify",
        "workdays_vacation",
    }
)


def list_supported_ingest_sources() -> tuple[str, ...]:
    """Return the supported ingest source names in deterministic order."""

    return tuple(sorted(_SUPPORTED_SOURCES))


def run_ingest_source(
    *,
    source: str,
    runtime: RuntimeContext,
    progress_callback: Callable[[JobProgressSnapshot], None] | None = None,
) -> (
    PhotoIngestionResult
    | CalendarIngestionResult
    | GoogleMapsTimelineIngestionResult
    | SpotifyIngestionResult
    | WorkdaysVacationIngestionResult
):
    """Run an ingestion entrypoint for a configured source."""

    if source not in _SUPPORTED_SOURCES:
        available_sources = ", ".join(list_supported_ingest_sources())
        raise ValueError(
            f"Unsupported source '{source}'. Available sources: {available_sources}."
        )

    if source == "photos":
        result = PhotoIngestionService().ingest(
            runtime=runtime,
            progress_callback=progress_callback,
        )
        logger.info(
            "ingest completed",
            extra={
                "source": source,
                "database_url": runtime.settings.database_url,
                "processed_asset_count": result.processed_asset_count,
                "error_count": result.error_count,
                "status": result.status,
                "run_id": result.run_id,
                "discovered_file_count": result.discovered_file_count,
                "analyzed_file_count": result.analyzed_file_count,
                "analysis_failed_file_count": result.analysis_failed_file_count,
                "assets_persisted": result.assets_persisted,
                "inserted_asset_count": result.inserted_asset_count,
                "updated_asset_count": result.updated_asset_count,
                "unchanged_asset_count": result.unchanged_asset_count,
                "skipped_asset_count": result.skipped_asset_count,
                "missing_from_source_count": result.missing_from_source_count,
                "metadata_batches_submitted": result.metadata_batches_submitted,
                "metadata_batches_completed": result.metadata_batches_completed,
            },
        )
        return result

    if source == "calendar":
        result = CalendarIngestionService().ingest(
            runtime=runtime,
            progress_callback=progress_callback,
        )
        logger.info(
            "ingest completed",
            extra={
                "source": source,
                "database_url": runtime.settings.database_url,
                "processed_document_count": result.processed_document_count,
                "persisted_source_count": result.persisted_source_count,
                "persisted_event_count": result.persisted_event_count,
                "error_count": result.error_count,
                "status": result.status,
                "run_id": result.run_id,
            },
        )
        return result

    if source == "spotify":
        result = SpotifyIngestionService().ingest(
            runtime=runtime,
            progress_callback=progress_callback,
        )
        logger.info(
            "ingest completed",
            extra={
                "source": source,
                "database_url": runtime.settings.database_url,
                "processed_document_count": result.processed_document_count,
                "persisted_source_count": result.persisted_source_count,
                "persisted_event_count": result.persisted_event_count,
                "skipped_json_file_count": result.skipped_json_file_count,
                "error_count": result.error_count,
                "status": result.status,
                "run_id": result.run_id,
            },
        )
        return result

    if source == "google_maps_timeline":
        result = GoogleMapsTimelineIngestionService().ingest(
            runtime=runtime,
            progress_callback=progress_callback,
        )
        logger.info(
            "ingest completed",
            extra={
                "source": source,
                "database_url": runtime.settings.database_url,
                "processed_document_count": result.processed_document_count,
                "persisted_source_count": result.persisted_source_count,
                "persisted_event_count": result.persisted_event_count,
                "error_count": result.error_count,
                "status": result.status,
                "run_id": result.run_id,
            },
        )
        return result

    if source == "workdays_vacation":
        result = WorkdaysVacationIngestionService().ingest(
            runtime=runtime,
            progress_callback=progress_callback,
        )
        logger.info(
            "ingest completed",
            extra={
                "source": source,
                "database_url": runtime.settings.database_url,
                "processed_workbook_count": result.processed_workbook_count,
                "persisted_source_count": result.persisted_source_count,
                "persisted_event_count": result.persisted_event_count,
                "error_count": result.error_count,
                "status": result.status,
                "run_id": result.run_id,
            },
        )
        return result

    raise AssertionError(f"Unhandled ingest source: {source}")
