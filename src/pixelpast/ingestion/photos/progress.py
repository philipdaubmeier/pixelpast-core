"""Stable progress import path and runtime adapter for photo ingestion."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from pixelpast.ingestion.photos.contracts import (
    PhotoDiscoveryError,
    PhotoMetadataBatchProgress,
)
from pixelpast.shared.job_progress_tracker import SharedJobProgressTrackerBase
from pixelpast.shared.progress import JobProgressCallback, JobProgressSnapshot
from pixelpast.shared.runtime import RuntimeContext

logger = logging.getLogger(__name__)

PhotoIngestionProgressSnapshot = JobProgressSnapshot


@dataclass(slots=True)
class PhotoIngestionProgressState:
    """Photo-specific counters tracked alongside the generic progress snapshot."""

    discovered_file_count: int = 0
    analyzed_file_count: int = 0
    failed: int = 0
    metadata_files_completed: int = 0
    metadata_batches_submitted: int = 0
    metadata_batches_completed: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0
    missing_from_source: int = 0

    def apply_discovery_count(self, *, discovered_file_count: int) -> None:
        """Replace the cumulative discovery count."""

        self.discovered_file_count = discovered_file_count

    def apply_missing_from_source_count(
        self,
        *,
        missing_from_source_count: int,
    ) -> None:
        """Replace the informational missing-from-source count."""

        self.missing_from_source = missing_from_source_count

    def apply_metadata_batch(self, progress: PhotoMetadataBatchProgress) -> None:
        """Advance photo-specific metadata batch counters for diagnostics/results."""

        if progress.event == "submitted":
            self.metadata_batches_submitted += 1
        elif progress.event == "completed":
            self.metadata_batches_completed += 1
            self.metadata_files_completed += progress.batch_size

    def mark_analysis_success(self) -> int:
        """Advance successful analysis progress and return phase completion."""

        self.analyzed_file_count += 1
        return self.analysis_completed_count

    def mark_analysis_failure(self) -> int:
        """Advance failed analysis progress and return phase completion."""

        self.failed += 1
        return self.analysis_completed_count

    def mark_persisted(self, *, outcome: str) -> None:
        """Advance persistence counters for one analyzed asset."""

        if outcome == "inserted":
            self.inserted += 1
        elif outcome == "updated":
            self.updated += 1
        elif outcome == "unchanged":
            self.unchanged += 1
        elif outcome == "skipped":
            self.skipped += 1
        else:
            raise ValueError(f"Unsupported persistence outcome: {outcome}")

    @property
    def analysis_completed_count(self) -> int:
        """Return the total analyzed or failed files in the current run."""

        return self.analyzed_file_count + self.failed

    @property
    def analysis_failed_file_count(self) -> int:
        """Return the photo-specific failed analysis count."""

        return self.failed

    @property
    def items_persisted(self) -> int:
        """Return the total persisted or reconciled canonical assets."""

        return self.inserted + self.updated + self.unchanged

    def to_progress_payload(
        self,
        *,
        total: int | None,
        completed: int,
    ) -> dict[str, int | None]:
        """Render the persisted generic progress JSON payload."""

        return {
            "total": total,
            "completed": completed,
            "inserted": self.inserted,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "skipped": self.skipped,
            "failed": self.failed,
            "missing_from_source": self.missing_from_source,
        }


class PhotoIngestionProgressTracker(
    SharedJobProgressTrackerBase[PhotoIngestionProgressState]
):
    """Photo-specific adapter over the generic ingestion progress engine."""

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
            state=PhotoIngestionProgressState(),
            job_type="ingest",
            job="photos",
            run_id=run_id,
            runtime=runtime,
            logger=logger,
            heartbeat_log_message="photo ingest heartbeat written",
            callback=callback,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
            now_factory=now_factory,
            monotonic_factory=monotonic_factory,
        )

    def start_phase(self, *, phase: str, total: int | None) -> None:
        """Enter a new operational phase and persist the transition immediately."""

        self._start_phase(
            phase=phase,
            total=total,
            log_message="photo ingest phase started",
        )

    def mark_discovered(self, *, path: str, discovered_file_count: int) -> None:
        """Update discovery counts as supported files are found."""

        self._state.apply_discovery_count(discovered_file_count=discovered_file_count)
        self._engine.state.set_phase_progress(
            completed=discovered_file_count,
            total=discovered_file_count,
        )
        logger.info(
            "photo ingest discovery progress",
            extra={
                "run_id": self._engine.state.run_id,
                "phase": self._engine.state.phase,
                "path": path,
                "completed": discovered_file_count,
            },
        )
        self._emit(event="progress")

    def finish_phase(self) -> None:
        """Persist the end of the current phase."""

        self._finish_phase(
            log_message="photo ingest phase completed",
        )

    def mark_missing_from_source(self, *, missing_from_source_count: int) -> None:
        """Record the informational count of known assets missing from the source."""

        self._state.apply_missing_from_source_count(
            missing_from_source_count=missing_from_source_count
        )
        logger.info(
            "photo ingest missing-from-source count",
            extra={
                "run_id": self._engine.state.run_id,
                "missing_from_source": missing_from_source_count,
            },
        )
        self._emit(event="progress", force_persist=True)

    def mark_metadata_batch(self, progress: PhotoMetadataBatchProgress) -> None:
        """Record metadata batch progress for logs and photo-specific summaries."""

        self._state.apply_metadata_batch(progress)
        if progress.event == "completed":
            self._engine.state.set_phase_progress(
                completed=min(
                    self._state.metadata_files_completed,
                    self._engine.state.total or self._state.metadata_files_completed,
                )
            )
        logger.info(
            "photo ingest metadata batch progress",
            extra={
                "run_id": self._engine.state.run_id,
                "phase": self._engine.state.phase,
                "batch_event": progress.event,
                "batch_index": progress.batch_index,
                "batch_total": progress.batch_total,
                "batch_size": progress.batch_size,
                "metadata_batches_submitted": self._state.metadata_batches_submitted,
                "metadata_batches_completed": self._state.metadata_batches_completed,
            },
        )
        self._emit(event="progress")

    def mark_analysis_success(self) -> None:
        """Record one successfully analyzed file."""

        self._engine.state.set_phase_progress(
            completed=max(
                self._engine.state.completed,
                self._state.mark_analysis_success(),
            ),
        )
        self._emit(event="progress")

    def mark_analysis_failure(self, *, error: PhotoDiscoveryError) -> None:
        """Record one file that failed during analysis."""

        self._engine.state.set_phase_progress(
            completed=max(
                self._engine.state.completed,
                self._state.mark_analysis_failure(),
            ),
        )
        logger.warning(
            "photo ingestion skipped file",
            extra={
                "run_id": self._engine.state.run_id,
                "phase": self._engine.state.phase,
                "path": error.path.as_posix(),
                "reason": error.message,
            },
        )
        self._emit(event="progress", force_persist=True)

    def mark_persisted(self, *, outcome: str) -> None:
        """Record one completed persistence outcome for an analyzed asset."""

        self._engine.state.increment_phase_completed()
        self._state.mark_persisted(outcome=outcome)
        logger.info(
            "photo ingest persistence progress",
            extra={
                "run_id": self._engine.state.run_id,
                "phase": self._engine.state.phase,
                "total": self._engine.state.total,
                "completed": self._engine.state.completed,
                "inserted": self._state.inserted,
                "updated": self._state.updated,
                "unchanged": self._state.unchanged,
                "skipped": self._state.skipped,
            },
        )
        self._emit(event="progress")

    def finish_run(self, *, status: str) -> JobProgressSnapshot:
        """Persist the terminal success or partial-failure state."""

        logger.info(
            "photo ingest finalization started",
            extra={
                "run_id": self._engine.state.run_id,
                "status": status,
            },
        )
        return self._finish_run(
            status=status,
            before_log_message="photo ingest finalization started",
            log_message="photo ingest completed",
        )

    def fail_run(self) -> JobProgressSnapshot:
        """Persist the terminal failed state using the current counters."""

        return self._fail_run(log_message="photo ingest failed")


__all__ = [
    "PhotoIngestionProgressSnapshot",
    "PhotoIngestionProgressTracker",
]
