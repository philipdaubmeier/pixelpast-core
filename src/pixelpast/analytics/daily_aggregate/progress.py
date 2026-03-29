"""Daily aggregate progress reporting over the shared job progress runtime."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from pixelpast.shared.job_progress_tracker import SharedJobProgressTrackerBase
from pixelpast.shared.progress import JobProgressCallback, JobProgressSnapshot
from pixelpast.shared.runtime import RuntimeContext

logger = logging.getLogger(__name__)

DAILY_AGGREGATE_JOB_NAME = "daily-aggregate"


@dataclass(slots=True)
class DailyAggregateProgressState:
    """Track derive counters mapped onto the shared progress contract.

    Semantics:
    - loading: `total=5`, one unit per canonical input bucket
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


class DailyAggregateProgressTracker(
    SharedJobProgressTrackerBase[DailyAggregateProgressState]
):
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
        super().__init__(
            state=DailyAggregateProgressState(),
            job_type="derive",
            job=DAILY_AGGREGATE_JOB_NAME,
            run_id=run_id,
            runtime=runtime,
            logger=logger,
            heartbeat_log_message="daily aggregate derive heartbeat written",
            callback=callback,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
            now_factory=now_factory,
            monotonic_factory=monotonic_factory,
        )

    def start_loading(self) -> None:
        """Enter canonical loading with one deterministic unit per input bucket."""

        self._start_phase(
            phase=self.loading_phase,
            total=5,
            log_message="daily aggregate derive phase started",
        )

    def mark_loading_bucket_completed(self) -> None:
        """Record one completed canonical input bucket."""

        self._engine.state.increment_phase_completed()
        self._emit(event="progress", force_persist=True)

    def start_building(self, *, total_input_count: int) -> None:
        """Enter aggregate construction using canonical contribution count as total."""

        self._start_phase(
            phase=self.building_phase,
            total=total_input_count,
            log_message="daily aggregate derive phase started",
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

        self._start_phase(
            phase=self.persistence_phase,
            total=aggregate_count,
            log_message="daily aggregate derive phase started",
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

        self._finish_phase()

    def finish_run(self, *, status: str) -> JobProgressSnapshot:
        """Persist terminal derive success."""

        return self._finish_run(
            status=status,
            log_message="daily aggregate derive completed",
        )

    def fail_run(self) -> JobProgressSnapshot:
        """Persist terminal derive failure."""

        return self._fail_run(log_message="daily aggregate derive failed")


__all__ = [
    "DAILY_AGGREGATE_JOB_NAME",
    "DailyAggregateProgressTracker",
]
