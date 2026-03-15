"""Stable progress import path and runtime adapter for calendar ingestion."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from pixelpast.ingestion.calendar.contracts import CalendarTransformError
from pixelpast.ingestion.calendar.fetch import CalendarDocumentLoadProgress
from pixelpast.shared.progress import (
    JobProgressCallback,
    JobProgressEngine,
    JobProgressSnapshot,
)
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
        normalized_outcome, event_count = _parse_document_outcome(outcome)
        self.persisted_event_count += event_count
        if normalized_outcome == "inserted":
            self.inserted += 1
        elif normalized_outcome == "updated":
            self.updated += 1
        elif normalized_outcome == "unchanged":
            self.unchanged += 1
        elif normalized_outcome == "skipped":
            self.skipped += 1
        else:
            raise ValueError(f"Unsupported persistence outcome: {normalized_outcome}")

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


class CalendarIngestionProgressTracker:
    """Calendar-specific adapter over the generic ingestion progress engine."""

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
        self._state = CalendarIngestionProgressState()
        self._engine = JobProgressEngine(
            job_type="ingest",
            job="calendar",
            run_id=run_id,
            runtime=runtime,
            payload_factory=self._progress_payload,
            snapshot_factory=self._build_snapshot,
            callback=callback,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
            now_factory=now_factory,
            monotonic_factory=monotonic_factory,
        )

    @property
    def counters(self) -> CalendarIngestionProgressState:
        return self._state

    def start_phase(self, *, phase: str, total: int | None) -> None:
        logger.info(
            "calendar ingest phase started",
            extra={"run_id": self._engine.state.run_id, "phase": phase, "total": total},
        )
        self._log_heartbeat_if_written(
            self._engine.start_phase(phase=phase, total=total)
        )

    def mark_discovered(self, *, path: str, discovered_file_count: int) -> None:
        self._state.apply_discovery_count(discovered_file_count=discovered_file_count)
        self._engine.state.set_phase_progress(
            completed=discovered_file_count,
            total=discovered_file_count,
        )
        logger.info(
            "calendar ingest discovery progress",
            extra={
                "run_id": self._engine.state.run_id,
                "phase": self._engine.state.phase,
                "path": path,
                "completed": discovered_file_count,
            },
        )
        self._emit(event="progress")

    def finish_phase(self) -> None:
        logger.info(
            "calendar ingest phase completed",
            extra={
                "run_id": self._engine.state.run_id,
                "phase": self._engine.state.phase,
                "total": self._engine.state.total,
                "completed": self._engine.state.completed,
            },
        )
        self._log_heartbeat_if_written(self._engine.finish_phase())

    def mark_missing_from_source(self, *, missing_from_source_count: int) -> None:
        self._state.apply_missing_from_source_count(
            missing_from_source_count=missing_from_source_count
        )
        self._emit(event="progress", force_persist=True)

    def mark_metadata_batch(self, progress: CalendarDocumentLoadProgress) -> None:
        self._state.apply_document_load(progress)
        if progress.event == "completed":
            self._engine.state.set_phase_progress(completed=self._state.documents_completed)
        self._emit(event="progress")

    def mark_analysis_success(self) -> None:
        self._engine.state.set_phase_progress(
            completed=max(
                self._engine.state.completed,
                self._state.mark_analysis_success(),
            )
        )
        self._emit(event="progress")

    def mark_analysis_failure(self, *, error: CalendarTransformError) -> None:
        self._engine.state.set_phase_progress(
            completed=max(
                self._engine.state.completed,
                self._state.mark_analysis_failure(),
            )
        )
        logger.warning(
            "calendar ingestion skipped document",
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
        snapshot = self._engine.finish_run(status=status)
        logger.info(
            "calendar ingest completed",
            extra={
                "run_id": self._engine.state.run_id,
                "status": status,
                **self._progress_payload(),
            },
        )
        return snapshot

    def fail_run(self) -> JobProgressSnapshot:
        snapshot = self._engine.fail_run()
        logger.error(
            "calendar ingest failed",
            extra={
                "run_id": self._engine.state.run_id,
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
    ) -> JobProgressSnapshot:
        snapshot = self._engine.emit(event=event, force_persist=force_persist)
        self._log_heartbeat_if_written(snapshot)
        return snapshot

    def _progress_payload(self) -> dict[str, int | str | None]:
        return self._state.to_progress_payload(
            total=self._engine.state.total,
            completed=self._engine.state.completed,
        )

    def _build_snapshot(
        self,
        event: str,
        heartbeat_written: bool,
    ) -> JobProgressSnapshot:
        return JobProgressSnapshot(
            event=event,
            job_type=self._engine.state.job_type,
            job=self._engine.state.job,
            run_id=self._engine.state.run_id,
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

    def _log_heartbeat_if_written(self, snapshot: JobProgressSnapshot) -> None:
        if not snapshot.heartbeat_written:
            return
        heartbeat_at = self._engine.last_heartbeat_at
        logger.info(
            "calendar ingest heartbeat written",
            extra={
                "run_id": self._engine.state.run_id,
                "phase": self._engine.state.phase,
                "last_heartbeat_at": (
                    heartbeat_at.isoformat() if heartbeat_at is not None else None
                ),
                "status": self._engine.state.status,
            },
        )


def _parse_document_outcome(outcome: str) -> tuple[str, int]:
    normalized_outcome, separator, event_count = outcome.partition(":")
    if not separator:
        return normalized_outcome, 0
    return normalized_outcome, int(event_count)


__all__ = [
    "CalendarIngestionProgressSnapshot",
    "CalendarIngestionProgressTracker",
]
