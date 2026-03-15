"""Shared phase-aware progress models and persistence runtime for job runs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic

from pixelpast.persistence.repositories import JobRunRepository
from pixelpast.shared.runtime import RuntimeContext


def build_initial_job_progress_payload() -> dict[str, int | None]:
    """Return the authoritative zeroed payload for a new job run."""

    return {
        "total": None,
        "completed": 0,
        "inserted": 0,
        "updated": 0,
        "unchanged": 0,
        "skipped": 0,
        "failed": 0,
        "missing_from_source": 0,
    }


@dataclass(slots=True, frozen=True)
class JobProgressSnapshot:
    """Phase-aware progress snapshot for one ingest or derive run."""

    event: str
    job_type: str
    job: str
    run_id: int
    phase: str
    status: str
    total: int | None
    completed: int
    inserted: int
    updated: int
    unchanged: int
    skipped: int
    failed: int
    missing_from_source: int
    heartbeat_written: bool


JobProgressCallback = Callable[[JobProgressSnapshot], None]
JobProgressPayloadFactory = Callable[[], dict[str, int | None]]
JobProgressSnapshotFactory = Callable[[str, bool], JobProgressSnapshot]

_UNSET = object()


@dataclass(slots=True)
class JobProgressState:
    """Mutable phase and lifecycle state for one operational job run."""

    job_type: str
    job: str
    run_id: int
    phase: str = "initializing"
    total: int | None = None
    completed: int = 0
    status: str = "running"

    def start_phase(self, *, phase: str, total: int | None) -> None:
        """Reset phase-local progress and enter a new operational phase."""

        self.phase = phase
        self.total = total
        self.completed = 0

    def set_phase_progress(
        self,
        *,
        completed: int,
        total: int | None | object = _UNSET,
    ) -> None:
        """Overwrite deterministic phase counters."""

        self.completed = completed
        if total is not _UNSET:
            self.total = total

    def increment_phase_completed(self, *, amount: int = 1) -> None:
        """Advance completed work within the current phase."""

        self.completed += amount

    def finish_phase(self) -> None:
        """Mark the current phase as completed."""

        if self.total is None:
            self.total = self.completed

    def start_terminal_phase(self, *, phase: str, status: str) -> None:
        """Enter the finalization phase with a terminal status."""

        self.status = status
        self.phase = phase
        self.total = 1
        self.completed = 1

    def mark_failed(self) -> None:
        """Record a terminal failure without changing the current phase."""

        self.status = "failed"


class JobProgressEngine:
    """Own the shared heartbeat, persistence, and callback mechanics."""

    def __init__(
        self,
        *,
        job_type: str,
        job: str,
        run_id: int,
        runtime: RuntimeContext,
        payload_factory: JobProgressPayloadFactory,
        snapshot_factory: JobProgressSnapshotFactory,
        callback: JobProgressCallback | None = None,
        heartbeat_interval_seconds: float = 10.0,
        now_factory: Callable[[], datetime] | None = None,
        monotonic_factory: Callable[[], float] | None = None,
    ) -> None:
        self.state = JobProgressState(
            job_type=job_type,
            job=job,
            run_id=run_id,
        )
        self._runtime = runtime
        self._payload_factory = payload_factory
        self._snapshot_factory = snapshot_factory
        self._callback = callback
        self._heartbeat_interval_seconds = heartbeat_interval_seconds
        self._now_factory = now_factory or _utc_now
        self._monotonic_factory = monotonic_factory or monotonic
        self._last_persist_monotonic: float | None = None
        self.last_heartbeat_at: datetime | None = None

    def start_phase(
        self,
        *,
        phase: str,
        total: int | None,
    ) -> JobProgressSnapshot:
        """Enter a new phase and persist the transition immediately."""

        self.state.start_phase(phase=phase, total=total)
        return self.emit(
            event="phase_started",
            force_persist=True,
        )

    def finish_phase(self) -> JobProgressSnapshot:
        """Persist completion of the current phase."""

        self.state.finish_phase()
        return self.emit(
            event="phase_completed",
            force_persist=True,
        )

    def emit(
        self,
        *,
        event: str,
        force_persist: bool = False,
    ) -> JobProgressSnapshot:
        """Persist a heartbeat if due and emit a snapshot."""

        heartbeat_written = self._persist_progress(force=force_persist)
        snapshot = self._snapshot_factory(
            event,
            heartbeat_written,
        )
        if self._callback is not None:
            self._callback(snapshot)
        return snapshot

    def finish_run(
        self,
        *,
        status: str,
        final_phase: str = "finalization",
    ) -> JobProgressSnapshot:
        """Persist a terminal success or partial-failure state."""

        self.state.start_terminal_phase(phase=final_phase, status=status)
        self.emit(
            event="phase_started",
            force_persist=True,
        )
        self._persist_terminal_state(status=status)
        snapshot = self._snapshot_factory(
            "run_finished",
            True,
        )
        if self._callback is not None:
            self._callback(snapshot)
        return snapshot

    def fail_run(self) -> JobProgressSnapshot:
        """Persist a terminal failed state using the current counters."""

        self.state.mark_failed()
        self._persist_terminal_state(status="failed")
        snapshot = self._snapshot_factory(
            "run_failed",
            True,
        )
        if self._callback is not None:
            self._callback(snapshot)
        return snapshot

    def _persist_progress(self, *, force: bool) -> bool:
        if not force and not self._heartbeat_due():
            return False

        self._persist_job_run(
            persist=lambda repository, heartbeat_at: repository.update_progress(
                run_id=self.state.run_id,
                phase=self.state.phase,
                progress_json=self._payload_factory(),
                last_heartbeat_at=heartbeat_at,
                status=self.state.status,
            )
        )
        return True

    def _persist_terminal_state(self, *, status: str) -> datetime:
        return self._persist_job_run(
            persist=lambda repository, heartbeat_at: repository.mark_finished_by_id(
                run_id=self.state.run_id,
                status=status,
                phase=self.state.phase,
                last_heartbeat_at=heartbeat_at,
                progress_json=self._payload_factory(),
            )
        )

    def _persist_job_run(
        self,
        *,
        persist: Callable[[JobRunRepository, datetime], object | None],
    ) -> datetime:
        heartbeat_at = self._now_factory()
        with self._runtime.session_factory() as session:
            repository = JobRunRepository(session)
            job_run = persist(repository, heartbeat_at)
            if job_run is None:
                raise RuntimeError(
                    f"JobRun {self.state.run_id} is missing from persistence."
                )
            session.commit()

        self.last_heartbeat_at = heartbeat_at
        self._last_persist_monotonic = self._monotonic_factory()
        return heartbeat_at

    def _heartbeat_due(self) -> bool:
        if self._last_persist_monotonic is None:
            return True
        return (
            self._monotonic_factory() - self._last_persist_monotonic
            >= self._heartbeat_interval_seconds
        )


def _utc_now() -> datetime:
    """Return the current aware UTC time."""

    return datetime.now(UTC)


__all__ = [
    "JobProgressCallback",
    "JobProgressEngine",
    "JobProgressSnapshot",
    "JobProgressState",
    "build_initial_job_progress_payload",
]
