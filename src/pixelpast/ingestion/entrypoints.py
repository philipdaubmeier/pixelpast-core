"""Ingestion command entrypoints."""

from collections.abc import Callable
import logging

from pixelpast.ingestion.progress import IngestionProgressSnapshot
from pixelpast.ingestion.photos.service import PhotoIngestionResult, PhotoIngestionService
from pixelpast.shared.runtime import RuntimeContext

logger = logging.getLogger(__name__)

_SUPPORTED_SOURCES = frozenset({"photos"})


def run_ingest_source(
    *,
    source: str,
    runtime: RuntimeContext,
    progress_callback: Callable[[IngestionProgressSnapshot], None] | None = None,
) -> PhotoIngestionResult:
    """Run an ingestion entrypoint for a configured source."""

    if source not in _SUPPORTED_SOURCES:
        available_sources = ", ".join(sorted(_SUPPORTED_SOURCES))
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
                "import_run_id": result.import_run_id,
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

    raise AssertionError(f"Unhandled ingest source: {source}")
