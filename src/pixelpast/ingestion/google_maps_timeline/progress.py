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
from pixelpast.shared.job_progress_tracker import SharedJobProgressTrackerBase
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
        _, _, detailed_counts = _parse_document_outcome(outcome)
        self.persisted_document_count += 1
        self.persisted_source_count += 1
        if detailed_counts is None:
            raise ValueError(f"Unsupported persistence outcome: {outcome}")
        self.inserted += detailed_counts["inserted"]
        self.updated += detailed_counts["updated"]
        self.unchanged += detailed_counts["unchanged"]
        self.skipped += detailed_counts["skipped"]
        self.persisted_event_count += detailed_counts["persisted_event_count"]

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
    SharedJobProgressTrackerBase[GoogleMapsTimelineIngestionProgressState]
):
    """Google Maps Timeline adapter over the generic ingestion progress engine."""

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
            job_type="ingest",
            job="google_maps_timeline",
            run_id=run_id,
            runtime=runtime,
            logger=logger,
            heartbeat_log_message="google maps timeline ingest heartbeat written",
            callback=callback,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
            now_factory=now_factory,
            monotonic_factory=monotonic_factory,
        )

    def start_phase(self, *, phase: str, total: int | None) -> None:
        self._start_phase(
            phase=phase,
            total=total,
            log_message="google maps timeline ingest phase started",
        )

    def finish_phase(self) -> None:
        self._finish_phase(
            log_message="google maps timeline ingest phase completed",
        )

    def mark_discovered(self, *, path: str, discovered_file_count: int) -> None:
        self._state.apply_discovery_count(
            discovered_export_count=discovered_file_count
        )
        self._engine.state.set_phase_progress(
            completed=discovered_file_count,
            total=discovered_file_count,
        )
        logger.info(
            "google maps timeline ingest discovery progress",
            extra={
                "run_id": self._engine.state.run_id,
                "phase": self._engine.state.phase,
                "path": path,
                "completed": discovered_file_count,
            },
        )
        self._emit(event="progress")

    def mark_missing_from_source(self, *, missing_from_source_count: int) -> None:
        self._state.apply_missing_from_source_count(
            missing_from_source_count=missing_from_source_count
        )
        self._emit(event="progress", force_persist=True)

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

    def mark_analysis_success(self) -> None:
        self._engine.state.set_phase_progress(
            completed=max(
                self._engine.state.completed,
                self._state.mark_analysis_success(),
            )
        )
        self._emit(event="progress")

    def mark_analysis_failure(
        self,
        *,
        error: GoogleMapsTimelineTransformError,
    ) -> None:
        self._engine.state.set_phase_progress(
            completed=max(
                self._engine.state.completed,
                self._state.mark_analysis_failure(),
            )
        )
        logger.warning(
            "google maps timeline ingestion skipped export",
            extra={
                "run_id": self._engine.state.run_id,
                "phase": self._engine.state.phase,
                "document": error.document.origin_label,
                "reason": error.message,
            },
        )
        self._emit(event="progress", force_persist=True)

    def mark_persisted(self, *, outcome: str) -> None:
        self._engine.state.increment_phase_completed()
        self._state.mark_persisted(outcome=outcome)
        self._emit(event="progress")

    def finish_run(self, *, status: str) -> JobProgressSnapshot:
        return self._finish_run(
            status=status,
            log_message="google maps timeline ingest completed",
        )

    def fail_run(self) -> JobProgressSnapshot:
        return self._fail_run(log_message="google maps timeline ingest failed")


def _parse_document_outcome(
    outcome: str,
) -> tuple[str, int, dict[str, int] | None]:
    if "=" in outcome and ";" in outcome:
        detailed_counts = {
            key: int(value)
            for key, value in (
                part.split("=", 1) for part in outcome.split(";") if part.strip()
            )
        }
        return (
            "detailed",
            detailed_counts.get("persisted_event_count", 0),
            {
                "inserted": detailed_counts.get("inserted", 0),
                "updated": detailed_counts.get("updated", 0),
                "unchanged": detailed_counts.get("unchanged", 0),
                "skipped": detailed_counts.get("skipped", 0),
                "persisted_event_count": detailed_counts.get(
                    "persisted_event_count",
                    0,
                ),
            },
        )
    return outcome, 0, None


__all__ = [
    "GoogleMapsTimelineIngestionProgressSnapshot",
    "GoogleMapsTimelineIngestionProgressTracker",
]
