"""Generic runtime progress models for ingestion jobs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class IngestionProgressSnapshot:
    """Phase-aware, source-agnostic progress snapshot for one ingest run."""

    event: str
    source: str
    import_run_id: int
    phase: str
    phase_status: str
    phase_total: int | None
    phase_completed: int
    status: str
    discovered_file_count: int
    analyzed_file_count: int
    analysis_failed_file_count: int
    metadata_batches_submitted: int
    metadata_batches_completed: int
    items_persisted: int
    inserted_item_count: int
    updated_item_count: int
    unchanged_item_count: int
    skipped_item_count: int
    missing_from_source_count: int
    current_batch_index: int | None
    current_batch_total: int | None
    current_batch_size: int | None
    heartbeat_written: bool


IngestionProgressCallback = Callable[[IngestionProgressSnapshot], None]
