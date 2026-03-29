"""Stable progress import path and runtime adapter for Google Maps Timeline."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from pixelpast.ingestion.google_maps_timeline.contracts import (
    GoogleMapsTimelineTransformError,
)
from pixelpast.ingestion.google_maps_timeline.fetch import (
    GoogleMapsTimelineDocumentLoadProgress,
)
from pixelpast.ingestion.progress_base import SharedIngestionProgressTrackerBase
from pixelpast.shared.persistence_outcome_summary import PersistenceOutcomeSummary
from pixelpast.shared.progress import JobProgressCallback, JobProgressSnapshot
from pixelpast.shared.runtime import RuntimeContext

logger = logging.getLogger(__name__)

GoogleMapsTimelineIngestionProgressSnapshot = JobProgressSnapshot


@dataclass(slots=True)
class GoogleMapsTimelineIngestionProgressState:
    """Google Maps Timeline counters tracked alongside the shared snapshot."""

    discovered_export_count: int = 0
    analyzed_export_count: int = 0
    failed: int = 0
    exports_submitted: int = 0
    exports_completed: int = 0
    persisted_document_count: int = 0
    persisted_source_count: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0
    missing_from_source: int = 0
    persisted_event_count: int = 0

    def apply_discovery_count(self, *, discovered_export_count: int) -> None:
        self.discovered_export_count = discovered_export_count

    def apply_missing_from_source_count(
        self,
        *,
        missing_from_source_count: int,
    ) -> None:
        self.missing_from_source = missing_from_source_count

    def apply_document_load(
        self,
        progress: GoogleMapsTimelineDocumentLoadProgress,
    ) -> None:
        if progress.event == "submitted":
            self.exports_submitted += 1
        elif progress.event == "completed":
            self.exports_completed += 1

    def mark_analysis_success(self) -> int:
        self.analyzed_export_count += 1
        return self.analysis_completed_count

    def mark_analysis_failure(self) -> int:
        self.failed += 1
        return self.analysis_completed_count

    def mark_persisted(self, *, outcome: str) -> None:
        summary = PersistenceOutcomeSummary.parse(outcome)
        self.persisted_document_count += 1
        self.persisted_source_count += 1
        if not summary.is_detailed:
            raise ValueError(f"Unsupported persistence outcome: {outcome}")
        self.inserted += summary.inserted
        self.updated += summary.updated
        self.unchanged += summary.unchanged
        self.skipped += summary.skipped
        self.persisted_event_count += summary.persisted_event_count

    @property
    def analysis_completed_count(self) -> int:
        return self.analyzed_export_count + self.failed

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
            "persisted_event_count": self.persisted_event_count,
        }


class GoogleMapsTimelineIngestionProgressTracker(
    SharedIngestionProgressTrackerBase[
        GoogleMapsTimelineIngestionProgressState,
        GoogleMapsTimelineTransformError,
    ]
):
    """Google Maps Timeline adapter over the generic ingestion progress engine."""

    analysis_failure_log_message = "google maps timeline ingestion skipped export"

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
            state=GoogleMapsTimelineIngestionProgressState(),
            job="google_maps_timeline",
            run_id=run_id,
            runtime=runtime,
            logger=logger,
            callback=callback,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
            now_factory=now_factory,
            monotonic_factory=monotonic_factory,
        )

    def mark_metadata_batch(
        self,
        progress: GoogleMapsTimelineDocumentLoadProgress,
    ) -> None:
        self._state.apply_document_load(progress)
        if progress.event == "completed":
            self._engine.state.set_phase_progress(
                completed=self._state.exports_completed
            )
        self._emit(event="progress")

    def _apply_discovery_count(self, *, discovered_file_count: int) -> None:
        self._state.apply_discovery_count(
            discovered_export_count=discovered_file_count
        )

    def _build_analysis_failure_log_extra(
        self,
        *,
        error: GoogleMapsTimelineTransformError,
    ) -> dict[str, object]:
        return {
            "document": error.document.origin_label,
            "reason": error.message,
        }

__all__ = [
    "GoogleMapsTimelineIngestionProgressSnapshot",
    "GoogleMapsTimelineIngestionProgressTracker",
]
