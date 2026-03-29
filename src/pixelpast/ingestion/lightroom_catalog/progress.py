"""Stable progress import path and runtime adapter for Lightroom ingestion."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from pixelpast.ingestion.lightroom_catalog.contracts import LightroomTransformError
from pixelpast.ingestion.lightroom_catalog.fetch import LightroomCatalogLoadProgress
from pixelpast.ingestion.progress_base import SharedIngestionProgressTrackerBase
from pixelpast.shared.persistence_outcome_summary import PersistenceOutcomeSummary
from pixelpast.shared.progress import JobProgressCallback, JobProgressSnapshot
from pixelpast.shared.runtime import RuntimeContext

logger = logging.getLogger(__name__)

LightroomCatalogIngestionProgressSnapshot = JobProgressSnapshot


@dataclass(slots=True)
class LightroomCatalogIngestionProgressState:
    """Lightroom-specific counters tracked alongside the generic snapshot."""

    discovered_catalog_count: int = 0
    analyzed_catalog_count: int = 0
    failed: int = 0
    catalogs_submitted: int = 0
    catalogs_completed: int = 0
    persisted_catalog_count: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0
    missing_from_source: int = 0
    persisted_asset_count: int = 0

    def apply_discovery_count(self, *, discovered_catalog_count: int) -> None:
        self.discovered_catalog_count = discovered_catalog_count

    def apply_missing_from_source_count(
        self,
        *,
        missing_from_source_count: int,
    ) -> None:
        self.missing_from_source = missing_from_source_count

    def apply_catalog_load(self, progress: LightroomCatalogLoadProgress) -> None:
        if progress.event == "submitted":
            self.catalogs_submitted += 1
        elif progress.event == "completed":
            self.catalogs_completed += 1

    def mark_analysis_success(self) -> int:
        self.analyzed_catalog_count += 1
        return self.analysis_completed_count

    def mark_analysis_failure(self) -> int:
        self.failed += 1
        return self.analysis_completed_count

    def mark_persisted(self, *, outcome: str) -> None:
        summary = PersistenceOutcomeSummary.parse(outcome)
        self.persisted_catalog_count += 1
        if not summary.is_detailed:
            raise ValueError(f"Unsupported persistence outcome: {outcome}")
        self.inserted += summary.inserted
        self.updated += summary.updated
        self.unchanged += summary.unchanged
        self.skipped += summary.skipped
        self.missing_from_source = summary.missing_from_source
        self.persisted_asset_count += summary.persisted_asset_count

    @property
    def analysis_completed_count(self) -> int:
        return self.analyzed_catalog_count + self.failed

    @property
    def processed_asset_count(self) -> int:
        return self.inserted + self.updated + self.unchanged

    def to_progress_payload(
        self,
        *,
        total: int | None,
        completed: int,
    ) -> dict[str, int | str | None]:
        return {
            "total": total,
            "completed": completed,
            "inserted": self.inserted,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "skipped": self.skipped,
            "failed": self.failed,
            "missing_from_source": self.missing_from_source,
            "persisted_asset_count": self.persisted_asset_count,
        }


class LightroomCatalogIngestionProgressTracker(
    SharedIngestionProgressTrackerBase[
        LightroomCatalogIngestionProgressState,
        LightroomTransformError,
    ]
):
    """Lightroom adapter over the generic ingestion progress engine."""

    analysis_failure_log_message = "lightroom catalog ingestion skipped catalog"

    def __init__(
        self,
        *,
        run_id: int,
        runtime: RuntimeContext,
        callback: JobProgressCallback | None = None,
        heartbeat_interval_seconds: float = 10.0,
        now_factory: Callable[[], datetime] | None = None,
        monotonic_factory: Callable[[], float] | None = None,
    ) -> None:
        super().__init__(
            state=LightroomCatalogIngestionProgressState(),
            job="lightroom_catalog",
            run_id=run_id,
            runtime=runtime,
            logger=logger,
            callback=callback,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
            now_factory=now_factory,
            monotonic_factory=monotonic_factory,
        )

    def mark_metadata_batch(self, progress: LightroomCatalogLoadProgress) -> None:
        self._state.apply_catalog_load(progress)
        if progress.event == "completed":
            self._engine.state.set_phase_progress(
                completed=self._state.catalogs_completed
            )
        self._emit(event="progress")

    def _apply_discovery_count(self, *, discovered_file_count: int) -> None:
        self._state.apply_discovery_count(
            discovered_catalog_count=discovered_file_count
        )

    def _build_analysis_failure_log_extra(
        self,
        *,
        error: LightroomTransformError,
    ) -> dict[str, object]:
        return {
            "catalog": error.catalog.origin_label,
            "reason": error.message,
        }

__all__ = [
    "LightroomCatalogIngestionProgressSnapshot",
    "LightroomCatalogIngestionProgressTracker",
]
