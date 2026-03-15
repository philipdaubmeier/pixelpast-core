"""Daily aggregate progress reporting over the shared job progress runtime."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from pixelpast.shared.progress import (
    JobProgressCallback,
    JobProgressEngine,
    JobProgressSnapshot,
)
from pixelpast.shared.runtime import RuntimeContext

logger = logging.getLogger(__name__)

DAILY_AGGREGATE_JOB_NAME = "daily-aggregate"


@dataclass(slots=True)
class DailyAggregateProgressState:
    """Track derive counters mapped onto the shared progress contract.

    Semantics:
    - loading: `total=4`, one unit per canonical input bucket
    - building: `total` equals the number of canonical contributions consumed
    - persisting: `total` equals the number of aggregate rows written
    - counters: `inserted` counts aggregate rows materialized by this run;
      the other shared counters remain zero for this job today
    """

    inserted: int = 0

    def to_progress_payload(
        self,
        *,
        total: int | None,
        completed: int,
    ) -> dict[str, int | None]:
        """Render the persisted shared progress JSON payload."""

        return {
            "total": total,
            "completed": completed,
            "inserted": self.inserted,
            "updated": 0,
            "unchanged": 0,
            "skipped": 0,
            "failed": 0,
            "missing_from_source": 0,
        }


class DailyAggregateProgressTracker:
    """Daily-aggregate-specific adapter over the shared job progress engine."""

    loading_phase = "loading canonical inputs"
    building_phase = "building daily aggregates"
    persistence_phase = "persisting daily aggregates"

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
        self._state = DailyAggregateProgressState()
        self._engine = JobProgressEngine(
            job_type="derive",
            job=DAILY_AGGREGATE_JOB_NAME,
            run_id=run_id,
            runtime=runtime,
            payload_factory=self._progress_payload,
            snapshot_factory=self._build_snapshot,
            callback=callback,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
            now_factory=now_factory,
            monotonic_factory=monotonic_factory,
        )

    def start_loading(self) -> None:
        """Enter canonical loading with one deterministic unit per input bucket."""

        self._log_phase_started(phase=self.loading_phase, total=4)
        self._log_heartbeat_if_written(
            self._engine.start_phase(phase=self.loading_phase, total=4)
        )

    def mark_loading_bucket_completed(self) -> None:
        """Record one completed canonical input bucket."""

        self._engine.state.increment_phase_completed()
        self._emit(event="progress", force_persist=True)

    def start_building(self, *, total_input_count: int) -> None:
        """Enter aggregate construction using canonical contribution count as total."""

        self._log_phase_started(phase=self.building_phase, total=total_input_count)
        self._log_heartbeat_if_written(
            self._engine.start_phase(
                phase=self.building_phase,
                total=total_input_count,
            )
        )

    def mark_build_completed(self, *, total_input_count: int) -> None:
        """Persist completion of aggregate construction."""

        self._engine.state.set_phase_progress(
            completed=total_input_count,
            total=total_input_count,
        )
        self._emit(event="progress", force_persist=True)

    def start_persisting(self, *, aggregate_count: int) -> None:
        """Enter aggregate persistence with one unit per output row."""

        self._log_phase_started(phase=self.persistence_phase, total=aggregate_count)
        self._log_heartbeat_if_written(
            self._engine.start_phase(
                phase=self.persistence_phase,
                total=aggregate_count,
            )
        )

    def mark_persisted(self, *, aggregate_count: int) -> None:
        """Persist aggregate write completion and derive outcome counters."""

        self._state.inserted = aggregate_count
        self._engine.state.set_phase_progress(
            completed=aggregate_count,
            total=aggregate_count,
        )
        self._emit(event="progress", force_persist=True)

    def finish_phase(self) -> None:
        """Persist completion of the current derive phase."""

        self._log_heartbeat_if_written(self._engine.finish_phase())

    def finish_run(self, *, status: str) -> JobProgressSnapshot:
        """Persist terminal derive success."""

        snapshot = self._engine.finish_run(status=status)
        logger.info(
            "daily aggregate derive completed",
            extra={
                "run_id": self._engine.state.run_id,
                "status": status,
                **self._progress_payload(),
            },
        )
        return snapshot

    def fail_run(self) -> JobProgressSnapshot:
        """Persist terminal derive failure."""

        snapshot = self._engine.fail_run()
        logger.error(
            "daily aggregate derive failed",
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
            updated=0,
            unchanged=0,
            skipped=0,
            failed=0,
            missing_from_source=0,
            heartbeat_written=heartbeat_written,
        )

    def _log_phase_started(self, *, phase: str, total: int | None) -> None:
        logger.info(
            "daily aggregate derive phase started",
            extra={
                "run_id": self._engine.state.run_id,
                "phase": phase,
                "total": total,
            },
        )

    def _log_heartbeat_if_written(self, snapshot: JobProgressSnapshot) -> None:
        if not snapshot.heartbeat_written:
            return

        heartbeat_at = self._engine.last_heartbeat_at
        logger.info(
            "daily aggregate derive heartbeat written",
            extra={
                "run_id": self._engine.state.run_id,
                "phase": self._engine.state.phase,
                "last_heartbeat_at": (
                    heartbeat_at.isoformat() if heartbeat_at is not None else None
                ),
                "status": self._engine.state.status,
            },
        )


__all__ = [
    "DAILY_AGGREGATE_JOB_NAME",
    "DailyAggregateProgressTracker",
]
