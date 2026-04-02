"""Progress reporting for the album aggregate derive job."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from pixelpast.shared.job_progress_tracker import SharedJobProgressTrackerBase
from pixelpast.shared.progress import JobProgressCallback, JobProgressSnapshot
from pixelpast.shared.runtime import RuntimeContext

logger = logging.getLogger(__name__)

ALBUM_AGGREGATE_JOB_NAME = "album-aggregate"


@dataclass(slots=True)
class AlbumAggregateProgressState:
    """Track derive counters under the shared progress contract."""

    inserted: int = 0

    def to_progress_payload(
        self,
        *,
        total: int | None,
        completed: int,
    ) -> dict[str, int | None]:
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


class AlbumAggregateProgressTracker(
    SharedJobProgressTrackerBase[AlbumAggregateProgressState]
):
    """Album-aggregate-specific adapter over the shared progress engine."""

    loading_phase = "loading album inputs"
    building_phase = "building album aggregates"
    persistence_phase = "persisting album aggregates"

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
            state=AlbumAggregateProgressState(),
            job_type="derive",
            job=ALBUM_AGGREGATE_JOB_NAME,
            run_id=run_id,
            runtime=runtime,
            logger=logger,
            heartbeat_log_message="album aggregate derive heartbeat written",
            callback=callback,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
            now_factory=now_factory,
            monotonic_factory=monotonic_factory,
        )

    def start_loading(self) -> None:
        self._start_phase(
            phase=self.loading_phase,
            total=5,
            log_message="album aggregate derive phase started",
        )

    def mark_loading_bucket_completed(self) -> None:
        self._engine.state.increment_phase_completed()
        self._emit(event="progress", force_persist=True)

    def start_building(self, *, total_input_count: int) -> None:
        self._start_phase(
            phase=self.building_phase,
            total=total_input_count,
            log_message="album aggregate derive phase started",
        )

    def mark_build_completed(self, *, total_input_count: int) -> None:
        self._engine.state.set_phase_progress(
            completed=total_input_count,
            total=total_input_count,
        )
        self._emit(event="progress", force_persist=True)

    def start_persisting(self, *, total_row_count: int) -> None:
        self._start_phase(
            phase=self.persistence_phase,
            total=total_row_count,
            log_message="album aggregate derive phase started",
        )

    def mark_persisted(self, *, total_row_count: int) -> None:
        self._state.inserted = total_row_count
        self._engine.state.set_phase_progress(
            completed=total_row_count,
            total=total_row_count,
        )
        self._emit(event="progress", force_persist=True)

    def finish_phase(self) -> None:
        self._finish_phase()

    def finish_run(self, *, status: str) -> JobProgressSnapshot:
        return self._finish_run(
            status=status,
            log_message="album aggregate derive completed",
        )

    def fail_run(self) -> JobProgressSnapshot:
        return self._fail_run(log_message="album aggregate derive failed")
