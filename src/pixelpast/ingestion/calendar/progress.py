"""Stable progress import path and runtime adapter for calendar ingestion."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from pixelpast.ingestion.calendar.contracts import CalendarTransformError
from pixelpast.ingestion.calendar.fetch import CalendarDocumentLoadProgress
from pixelpast.ingestion.progress_base import SharedIngestionProgressTrackerBase
from pixelpast.shared.persistence_outcome_summary import PersistenceOutcomeSummary
from pixelpast.shared.progress import JobProgressCallback, JobProgressSnapshot
from pixelpast.shared.runtime import RuntimeContext

logger = logging.getLogger(__name__)

CalendarIngestionProgressSnapshot = JobProgressSnapshot


@dataclass(slots=True)
class CalendarIngestionProgressState:
    """Calendar-specific counters tracked alongside the generic progress snapshot."""

    discovered_file_count: int = 0
    analyzed_file_count: int = 0
    failed: int = 0
    documents_submitted: int = 0
    documents_completed: int = 0
    persisted_document_count: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0
    missing_from_source: int = 0
    persisted_event_count: int = 0

    def apply_discovery_count(self, *, discovered_file_count: int) -> None:
        self.discovered_file_count = discovered_file_count

    def apply_missing_from_source_count(
        self,
        *,
        missing_from_source_count: int,
    ) -> None:
        self.missing_from_source = missing_from_source_count

    def apply_document_load(self, progress: CalendarDocumentLoadProgress) -> None:
        if progress.event == "submitted":
            self.documents_submitted += 1
        elif progress.event == "completed":
            self.documents_completed += 1

    def mark_analysis_success(self) -> int:
        self.analyzed_file_count += 1
        return self.analysis_completed_count

    def mark_analysis_failure(self) -> int:
        self.failed += 1
        return self.analysis_completed_count

    def mark_persisted(self, *, outcome: str) -> None:
        summary = PersistenceOutcomeSummary.parse(outcome)
        self.persisted_document_count += 1
        if summary.is_detailed:
            self.inserted += summary.inserted
            self.updated += summary.updated
            self.unchanged += summary.unchanged
            self.skipped += summary.skipped
            self.persisted_event_count += summary.persisted_event_count
            return

        self.persisted_event_count += summary.persisted_event_count
        if summary.simple_outcome == "inserted":
            self.inserted += summary.persisted_event_count
        elif summary.simple_outcome == "updated":
            self.updated += summary.persisted_event_count
        elif summary.simple_outcome == "unchanged":
            self.unchanged += summary.persisted_event_count
        elif summary.simple_outcome == "skipped":
            self.skipped += summary.persisted_event_count
        else:
            raise ValueError(f"Unsupported persistence outcome: {summary.simple_outcome}")

    @property
    def analysis_completed_count(self) -> int:
        return self.analyzed_file_count + self.failed

    @property
    def items_persisted(self) -> int:
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
            "persisted_event_count": self.persisted_event_count,
        }


class CalendarIngestionProgressTracker(
    SharedIngestionProgressTrackerBase[
        CalendarIngestionProgressState,
        CalendarTransformError,
    ]
):
    """Calendar-specific adapter over the generic ingestion progress engine."""

    analysis_failure_log_message = "calendar ingestion skipped document"

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
            state=CalendarIngestionProgressState(),
            job="calendar",
            run_id=run_id,
            runtime=runtime,
            logger=logger,
            callback=callback,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
            now_factory=now_factory,
            monotonic_factory=monotonic_factory,
        )

    def mark_metadata_batch(self, progress: CalendarDocumentLoadProgress) -> None:
        self._state.apply_document_load(progress)
        if progress.event == "completed":
            self._engine.state.set_phase_progress(completed=self._state.documents_completed)
        self._emit(event="progress")

    def _build_analysis_failure_log_extra(
        self,
        *,
        error: CalendarTransformError,
    ) -> dict[str, object]:
        return {
            "document": error.document.origin_label,
            "reason": error.message,
        }

__all__ = [
    "CalendarIngestionProgressSnapshot",
    "CalendarIngestionProgressTracker",
]
