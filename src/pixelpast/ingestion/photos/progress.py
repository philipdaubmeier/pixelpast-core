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
    """Photo-specific counters and batch cursor for progress snapshots."""

    discovered_file_count: int = 0
    analyzed_file_count: int = 0
    analysis_failed_file_count: int = 0
    metadata_batches_submitted: int = 0
    metadata_batches_completed: int = 0
    items_persisted: int = 0
    inserted_item_count: int = 0
    updated_item_count: int = 0
    unchanged_item_count: int = 0
    skipped_item_count: int = 0
    missing_from_source_count: int = 0
    current_batch_index: int | None = None
    current_batch_total: int | None = None
    current_batch_size: int | None = None

    def apply_discovery_count(self, *, discovered_file_count: int) -> None:
        """Replace the cumulative discovery count."""

        self.discovered_file_count = discovered_file_count

    def apply_missing_from_source_count(
        self,
        *,
        missing_from_source_count: int,
    ) -> None:
        """Replace the informational missing-from-source count."""

        self.missing_from_source_count = missing_from_source_count

    def apply_metadata_batch(self, progress: PhotoMetadataBatchProgress) -> None:
        """Advance batch counters and keep the current batch cursor in sync."""

        self.current_batch_index = progress.batch_index
        self.current_batch_total = progress.batch_total
        self.current_batch_size = progress.batch_size
        if progress.event == "submitted":
            self.metadata_batches_submitted += 1
        elif progress.event == "completed":
            self.metadata_batches_completed += 1

    def mark_analysis_success(self) -> int:
        """Advance successful analysis progress and return total completed work."""

        self.analyzed_file_count += 1
        return self.analysis_completed_count

    def mark_analysis_failure(self) -> int:
        """Advance failed analysis progress and return total completed work."""

        self.analysis_failed_file_count += 1
        return self.analysis_completed_count

    def mark_persisted(self, *, outcome: str) -> None:
        """Advance persistence counters for one analyzed asset."""

        if outcome == "inserted":
            self.inserted_item_count += 1
            self.items_persisted += 1
        elif outcome == "updated":
            self.updated_item_count += 1
            self.items_persisted += 1
        elif outcome == "unchanged":
            self.unchanged_item_count += 1
            self.items_persisted += 1
        elif outcome == "skipped":
            self.skipped_item_count += 1
        else:
            raise ValueError(f"Unsupported persistence outcome: {outcome}")

    @property
    def analysis_completed_count(self) -> int:
        """Return the total analyzed or failed files in the current run."""

        return self.analyzed_file_count + self.analysis_failed_file_count

    def clear_batch_cursor(self) -> None:
        """Clear the transient batch cursor when a phase starts."""

        self.current_batch_index = None
        self.current_batch_total = None
        self.current_batch_size = None

    def to_progress_payload(
        self,
        *,
        phase_total: int | None,
        phase_completed: int,
    ) -> dict[str, int | None]:
        """Render the persisted progress JSON payload."""

        return {
            "phase_total": phase_total,
            "phase_completed": phase_completed,
            "discovered_file_count": self.discovered_file_count,
            "analyzed_file_count": self.analyzed_file_count,
            "analysis_failed_file_count": self.analysis_failed_file_count,
            "metadata_batches_submitted": self.metadata_batches_submitted,
            "metadata_batches_completed": self.metadata_batches_completed,
            "items_persisted": self.items_persisted,
            "inserted_item_count": self.inserted_item_count,
            "updated_item_count": self.updated_item_count,
            "unchanged_item_count": self.unchanged_item_count,
            "skipped_item_count": self.skipped_item_count,
            "missing_from_source_count": self.missing_from_source_count,
            "current_batch_index": self.current_batch_index,
            "current_batch_total": self.current_batch_total,
            "current_batch_size": self.current_batch_size,
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

        self._state.clear_batch_cursor()
        logger.info(
            "photo ingest phase started",
            extra={
                "import_run_id": self._engine.state.import_run_id,
                "phase": phase,
                "phase_total": total,
            },
        )
        self._log_heartbeat_if_written(
            self._engine.start_phase(phase=phase, total=total)
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
                "import_run_id": self._engine.state.import_run_id,
                "phase": self._engine.state.phase,
                "path": path,
                "discovered_file_count": discovered_file_count,
            },
        )
        self._emit(event="progress", phase_status="running")

    def finish_phase(self) -> None:
        """Persist the end of the current phase."""

        logger.info(
            "photo ingest phase completed",
            extra={
                "import_run_id": self._engine.state.import_run_id,
                "phase": self._engine.state.phase,
                "phase_total": self._engine.state.phase_total,
                "phase_completed": self._engine.state.phase_completed,
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
                "missing_from_source_count": missing_from_source_count,
            },
        )
        self._emit(event="progress", phase_status="running", force_persist=True)

    def mark_metadata_batch(self, progress: PhotoMetadataBatchProgress) -> None:
        """Record metadata batch submission and completion progress."""

        self._state.apply_metadata_batch(progress)
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
        self._emit(event=f"metadata_batch_{progress.event}", phase_status="running")

    def mark_analysis_success(self) -> None:
        """Record one successfully analyzed file."""

        self._engine.state.set_phase_progress(
            completed=self._state.mark_analysis_success(),
        )
        self._emit(event="progress", phase_status="running")

    def mark_analysis_failure(self, *, error: PhotoDiscoveryError) -> None:
        """Record one file that failed during analysis."""

        self._engine.state.set_phase_progress(
            completed=self._state.mark_analysis_failure(),
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
        self._emit(event="progress", phase_status="running", force_persist=True)

    def mark_persisted(self, *, outcome: str) -> None:
        """Record one completed persistence outcome for an analyzed asset."""

        self._engine.state.increment_phase_completed()
        self._state.mark_persisted(outcome=outcome)
        logger.info(
            "photo ingest persistence progress",
            extra={
                "import_run_id": self._engine.state.import_run_id,
                "phase": self._engine.state.phase,
                "phase_total": self._engine.state.phase_total,
                "phase_completed": self._engine.state.phase_completed,
                "items_persisted": self._state.items_persisted,
                "inserted_item_count": self._state.inserted_item_count,
                "updated_item_count": self._state.updated_item_count,
                "unchanged_item_count": self._state.unchanged_item_count,
                "skipped_item_count": self._state.skipped_item_count,
            },
        )
        self._emit(event="progress", phase_status="running")

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
        phase_status: str,
        force_persist: bool = False,
    ) -> IngestionProgressSnapshot:
        snapshot = self._engine.emit(
            event=event,
            phase_status=phase_status,
            force_persist=force_persist,
        )
        self._log_heartbeat_if_written(snapshot)
        return snapshot

    def _progress_payload(self) -> dict[str, int | None]:
        return self._state.to_progress_payload(
            phase_total=self._engine.state.phase_total,
            phase_completed=self._engine.state.phase_completed,
        )

    def _build_snapshot(
        self,
        event: str,
        phase_status: str,
        heartbeat_written: bool,
    ) -> IngestionProgressSnapshot:
        return IngestionProgressSnapshot(
            event=event,
            source=self._engine.state.source,
            import_run_id=self._engine.state.import_run_id,
            phase=self._engine.state.phase,
            phase_status=phase_status,
            phase_total=self._engine.state.phase_total,
            phase_completed=self._engine.state.phase_completed,
            status=self._engine.state.status,
            discovered_file_count=self._state.discovered_file_count,
            analyzed_file_count=self._state.analyzed_file_count,
            analysis_failed_file_count=self._state.analysis_failed_file_count,
            metadata_batches_submitted=self._state.metadata_batches_submitted,
            metadata_batches_completed=self._state.metadata_batches_completed,
            items_persisted=self._state.items_persisted,
            inserted_item_count=self._state.inserted_item_count,
            updated_item_count=self._state.updated_item_count,
            unchanged_item_count=self._state.unchanged_item_count,
            skipped_item_count=self._state.skipped_item_count,
            missing_from_source_count=self._state.missing_from_source_count,
            current_batch_index=self._state.current_batch_index,
            current_batch_total=self._state.current_batch_total,
            current_batch_size=self._state.current_batch_size,
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
