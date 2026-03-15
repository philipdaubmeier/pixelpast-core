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
from pixelpast.ingestion.progress import (
    IngestionProgressCallback,
    IngestionProgressEngine,
    IngestionProgressSnapshot,
)
from pixelpast.shared.runtime import RuntimeContext

logger = logging.getLogger(__name__)

PhotoIngestionProgressSnapshot = IngestionProgressSnapshot


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


class PhotoIngestionProgressTracker:
    """Photo-specific adapter over the generic ingestion progress engine."""

    def __init__(
        self,
        *,
        import_run_id: int,
        runtime: RuntimeContext,
        callback: IngestionProgressCallback | None = None,
        heartbeat_interval_seconds: float = 10.0,
        now_factory: Callable[[], datetime] | None = None,
        monotonic_factory: Callable[[], float] | None = None,
    ) -> None:
        self._state = PhotoIngestionProgressState()
        self._engine = IngestionProgressEngine(
            source="photos",
            import_run_id=import_run_id,
            runtime=runtime,
            payload_factory=self._progress_payload,
            snapshot_factory=self._build_snapshot,
            callback=callback,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
            now_factory=now_factory,
            monotonic_factory=monotonic_factory,
        )

    @property
    def counters(self) -> PhotoIngestionProgressState:
        """Expose the current counters for final result construction."""

        return self._state

    def start_phase(self, *, phase: str, total: int | None) -> None:
        """Enter a new operational phase and persist the transition immediately."""

        logger.info(
            "photo ingest phase started",
            extra={
                "import_run_id": self._engine.state.import_run_id,
                "phase": phase,
                "total": total,
            },
        )
        self._log_heartbeat_if_written(self._engine.start_phase(phase=phase, total=total))

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
                "import_run_id": self._engine.state.import_run_id,
                "phase": self._engine.state.phase,
                "path": path,
                "completed": discovered_file_count,
            },
        )
        self._emit(event="progress")

    def finish_phase(self) -> None:
        """Persist the end of the current phase."""

        logger.info(
            "photo ingest phase completed",
            extra={
                "import_run_id": self._engine.state.import_run_id,
                "phase": self._engine.state.phase,
                "total": self._engine.state.total,
                "completed": self._engine.state.completed,
            },
        )
        self._log_heartbeat_if_written(self._engine.finish_phase())

    def mark_missing_from_source(self, *, missing_from_source_count: int) -> None:
        """Record the informational count of known assets missing from the source."""

        self._state.apply_missing_from_source_count(
            missing_from_source_count=missing_from_source_count
        )
        logger.info(
            "photo ingest missing-from-source count",
            extra={
                "import_run_id": self._engine.state.import_run_id,
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
                "import_run_id": self._engine.state.import_run_id,
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
                "import_run_id": self._engine.state.import_run_id,
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
                "import_run_id": self._engine.state.import_run_id,
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

    def finish_run(self, *, status: str) -> IngestionProgressSnapshot:
        """Persist the terminal success or partial-failure state."""

        logger.info(
            "photo ingest finalization started",
            extra={
                "import_run_id": self._engine.state.import_run_id,
                "status": status,
            },
        )
        snapshot = self._engine.finish_run(status=status)
        logger.info(
            "photo ingest completed",
            extra={
                "import_run_id": self._engine.state.import_run_id,
                "status": status,
                **self._progress_payload(),
            },
        )
        return snapshot

    def fail_run(self) -> IngestionProgressSnapshot:
        """Persist the terminal failed state using the current counters."""

        snapshot = self._engine.fail_run()
        logger.error(
            "photo ingest failed",
            extra={
                "import_run_id": self._engine.state.import_run_id,
                "phase": self._engine.state.phase,
                **self._progress_payload(),
            },
        )
        return snapshot

    def _emit(
        self,
        *,
        event: str,
        force_persist: bool = False,
    ) -> IngestionProgressSnapshot:
        snapshot = self._engine.emit(
            event=event,
            force_persist=force_persist,
        )
        self._log_heartbeat_if_written(snapshot)
        return snapshot

    def _progress_payload(self) -> dict[str, int | None]:
        return self._state.to_progress_payload(
            total=self._engine.state.total,
            completed=self._engine.state.completed,
        )

    def _build_snapshot(
        self,
        event: str,
        heartbeat_written: bool,
    ) -> IngestionProgressSnapshot:
        return IngestionProgressSnapshot(
            event=event,
            source=self._engine.state.source,
            import_run_id=self._engine.state.import_run_id,
            phase=self._engine.state.phase,
            status=self._engine.state.status,
            total=self._engine.state.total,
            completed=self._engine.state.completed,
            inserted=self._state.inserted,
            updated=self._state.updated,
            unchanged=self._state.unchanged,
            skipped=self._state.skipped,
            failed=self._state.failed,
            missing_from_source=self._state.missing_from_source,
            heartbeat_written=heartbeat_written,
        )

    def _log_heartbeat_if_written(self, snapshot: IngestionProgressSnapshot) -> None:
        if not snapshot.heartbeat_written:
            return
        heartbeat_at = self._engine.last_heartbeat_at
        logger.info(
            "photo ingest heartbeat written",
            extra={
                "import_run_id": self._engine.state.import_run_id,
                "phase": self._engine.state.phase,
                "last_heartbeat_at": (
                    heartbeat_at.isoformat() if heartbeat_at is not None else None
                ),
                "status": self._engine.state.status,
            },
        )


__all__ = [
    "PhotoIngestionProgressSnapshot",
    "PhotoIngestionProgressTracker",
]
