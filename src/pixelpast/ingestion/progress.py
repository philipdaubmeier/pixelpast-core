"""Generic runtime progress models and engine for ingestion jobs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic

from pixelpast.persistence.repositories import ImportRunRepository
from pixelpast.shared.runtime import RuntimeContext


@dataclass(slots=True, frozen=True)
class IngestionProgressSnapshot:
    """Phase-aware, source-agnostic progress snapshot for one ingest run."""

    event: str
    source: str
    import_run_id: int
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


IngestionProgressCallback = Callable[[IngestionProgressSnapshot], None]
IngestionProgressPayloadFactory = Callable[[], dict[str, int | None]]
IngestionProgressSnapshotFactory = Callable[
    [str, bool],
    IngestionProgressSnapshot,
]

_UNSET = object()


@dataclass(slots=True)
class IngestionProgressState:
    """Mutable phase and lifecycle state for one ingest run."""

    source: str
    import_run_id: int
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


class IngestionProgressEngine:
    """Own the generic heartbeat, persistence, and callback mechanics."""

    def __init__(
        self,
        *,
        source: str,
        import_run_id: int,
        runtime: RuntimeContext,
        payload_factory: IngestionProgressPayloadFactory,
        snapshot_factory: IngestionProgressSnapshotFactory,
        callback: IngestionProgressCallback | None = None,
        heartbeat_interval_seconds: float = 10.0,
        now_factory: Callable[[], datetime] | None = None,
        monotonic_factory: Callable[[], float] | None = None,
    ) -> None:
        self.state = IngestionProgressState(
            source=source,
            import_run_id=import_run_id,
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
    ) -> IngestionProgressSnapshot:
        """Enter a new phase and persist the transition immediately."""

        self.state.start_phase(phase=phase, total=total)
        return self.emit(
            event="phase_started",
            force_persist=True,
        )

    def finish_phase(self) -> IngestionProgressSnapshot:
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
    ) -> IngestionProgressSnapshot:
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
    ) -> IngestionProgressSnapshot:
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

    def fail_run(self) -> IngestionProgressSnapshot:
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

        heartbeat_at = self._now_factory()
        with self._runtime.session_factory() as session:
            repository = ImportRunRepository(session)
            import_run = repository.update_progress(
                import_run_id=self.state.import_run_id,
                phase=self.state.phase,
                progress_json=self._payload_factory(),
                last_heartbeat_at=heartbeat_at,
                status=self.state.status,
            )
            if import_run is None:
                raise RuntimeError(
                    f"ImportRun {self.state.import_run_id} is missing from persistence."
                )
            session.commit()

        self.last_heartbeat_at = heartbeat_at
        self._last_persist_monotonic = self._monotonic_factory()
        return True

    def _persist_terminal_state(self, *, status: str) -> datetime:
        heartbeat_at = self._now_factory()
        with self._runtime.session_factory() as session:
            repository = ImportRunRepository(session)
            import_run = repository.mark_finished_by_id(
                import_run_id=self.state.import_run_id,
                status=status,
                phase=self.state.phase,
                last_heartbeat_at=heartbeat_at,
                progress_json=self._payload_factory(),
            )
            if import_run is None:
                raise RuntimeError(
                    f"ImportRun {self.state.import_run_id} is missing from persistence."
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
