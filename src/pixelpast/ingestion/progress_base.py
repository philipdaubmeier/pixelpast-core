"""Shared staged-ingestion tracker shell above the generic job tracker base."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Generic, TypeVar

from pixelpast.shared.job_progress_tracker import SharedJobProgressTrackerBase
from pixelpast.shared.progress import JobProgressCallback, JobProgressSnapshot
from pixelpast.shared.runtime import RuntimeContext

StateT = TypeVar("StateT")
ErrorT = TypeVar("ErrorT")


class SharedIngestionProgressTrackerBase(
    SharedJobProgressTrackerBase[StateT],
    Generic[StateT, ErrorT],
):
    """Provide the repeated staged-ingestion tracker mechanics."""

    analysis_failure_log_message: str

    def __init__(
        self,
        *,
        state: StateT,
        job: str,
        run_id: int,
        runtime: RuntimeContext,
        logger,
        callback: JobProgressCallback | None = None,
        heartbeat_interval_seconds: float = 10.0,
        now_factory: Callable[[], datetime] | None = None,
        monotonic_factory: Callable[[], float] | None = None,
    ) -> None:
        super().__init__(
            state=state,
            job_type="ingest",
            job=job,
            run_id=run_id,
            runtime=runtime,
            logger=logger,
            heartbeat_log_message=f"{job} heartbeat written",
            callback=callback,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
            now_factory=now_factory,
            monotonic_factory=monotonic_factory,
        )

    def start_phase(self, *, phase: str, total: int | None) -> None:
        self._start_phase(
            phase=phase,
            total=total,
            log_message=self._job_log_message("phase started"),
        )

    def finish_phase(self) -> None:
        self._finish_phase(
            log_message=self._job_log_message("phase completed"),
        )

    def mark_discovered(self, *, path: str, discovered_file_count: int) -> None:
        self._apply_discovery_count(discovered_file_count=discovered_file_count)
        self._engine.state.set_phase_progress(
            completed=discovered_file_count,
            total=discovered_file_count,
        )
        self._logger.info(
            self._job_log_message("discovery progress"),
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

    def mark_analysis_success(self) -> None:
        self._engine.state.set_phase_progress(
            completed=max(
                self._engine.state.completed,
                self._state.mark_analysis_success(),
            )
        )
        self._emit(event="progress")

    def mark_analysis_failure(self, *, error: ErrorT) -> None:
        self._engine.state.set_phase_progress(
            completed=max(
                self._engine.state.completed,
                self._state.mark_analysis_failure(),
            )
        )
        self._logger.warning(
            self.analysis_failure_log_message,
            extra={
                "run_id": self._engine.state.run_id,
                "phase": self._engine.state.phase,
                **self._build_analysis_failure_log_extra(error=error),
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
            log_message=self._job_log_message("completed"),
        )

    def fail_run(self) -> JobProgressSnapshot:
        return self._fail_run(log_message=self._job_log_message("failed"))

    def _job_log_message(self, suffix: str) -> str:
        return f"{self._engine.state.job} {suffix}"

    def _apply_discovery_count(self, *, discovered_file_count: int) -> None:
        self._state.apply_discovery_count(discovered_file_count=discovered_file_count)

    def _build_analysis_failure_log_extra(self, *, error: ErrorT) -> dict[str, object]:
        raise NotImplementedError


__all__ = ["SharedIngestionProgressTrackerBase"]
