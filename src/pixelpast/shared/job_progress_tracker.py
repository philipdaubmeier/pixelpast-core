"""Shared tracker shell over the job progress engine."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Generic, TypeVar

from pixelpast.shared.progress import (
    JobProgressCallback,
    JobProgressEngine,
    JobProgressSnapshot,
)
from pixelpast.shared.runtime import RuntimeContext

StateT = TypeVar("StateT")


class SharedJobProgressTrackerBase(Generic[StateT]):
    """Provide the repeated tracker mechanics above ``JobProgressEngine``."""

    def __init__(
        self,
        *,
        state: StateT,
        job_type: str,
        job: str,
        run_id: int,
        runtime: RuntimeContext,
        logger: logging.Logger,
        heartbeat_log_message: str,
        callback: JobProgressCallback | None = None,
        heartbeat_interval_seconds: float = 10.0,
        now_factory: Callable[[], datetime] | None = None,
        monotonic_factory: Callable[[], float] | None = None,
    ) -> None:
        self._state = state
        self._logger = logger
        self._heartbeat_log_message = heartbeat_log_message
        self._engine = JobProgressEngine(
            job_type=job_type,
            job=job,
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
    def counters(self) -> StateT:
        return self._state

    def _start_phase(
        self,
        *,
        phase: str,
        total: int | None,
        log_message: str | None = None,
    ) -> JobProgressSnapshot:
        if log_message is not None:
            self._logger.info(
                log_message,
                extra={
                    "run_id": self._engine.state.run_id,
                    "phase": phase,
                    "total": total,
                },
            )
        snapshot = self._engine.start_phase(phase=phase, total=total)
        self._log_heartbeat_if_written(snapshot)
        return snapshot

    def _finish_phase(
        self,
        *,
        log_message: str | None = None,
    ) -> JobProgressSnapshot:
        if log_message is not None:
            self._logger.info(
                log_message,
                extra={
                    "run_id": self._engine.state.run_id,
                    "phase": self._engine.state.phase,
                    "total": self._engine.state.total,
                    "completed": self._engine.state.completed,
                },
            )
        snapshot = self._engine.finish_phase()
        self._log_heartbeat_if_written(snapshot)
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

    def _finish_run(
        self,
        *,
        status: str,
        log_message: str,
        before_log_message: str | None = None,
    ) -> JobProgressSnapshot:
        if before_log_message is not None:
            self._logger.info(
                before_log_message,
                extra={
                    "run_id": self._engine.state.run_id,
                    "status": status,
                },
            )
        snapshot = self._engine.finish_run(status=status)
        self._logger.info(
            log_message,
            extra={
                "run_id": self._engine.state.run_id,
                "status": status,
                **self._progress_payload(),
            },
        )
        return snapshot

    def _fail_run(self, *, log_message: str) -> JobProgressSnapshot:
        snapshot = self._engine.fail_run()
        self._logger.error(
            log_message,
            extra={
                "run_id": self._engine.state.run_id,
                "phase": self._engine.state.phase,
                **self._progress_payload(),
            },
        )
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
        payload = self._progress_payload()
        return JobProgressSnapshot(
            event=event,
            job_type=self._engine.state.job_type,
            job=self._engine.state.job,
            run_id=self._engine.state.run_id,
            phase=self._engine.state.phase,
            status=self._engine.state.status,
            total=self._engine.state.total,
            completed=self._engine.state.completed,
            inserted=int(payload.get("inserted") or 0),
            updated=int(payload.get("updated") or 0),
            unchanged=int(payload.get("unchanged") or 0),
            skipped=int(payload.get("skipped") or 0),
            failed=int(payload.get("failed") or 0),
            missing_from_source=int(payload.get("missing_from_source") or 0),
            heartbeat_written=heartbeat_written,
        )

    def _log_heartbeat_if_written(self, snapshot: JobProgressSnapshot) -> None:
        if not snapshot.heartbeat_written:
            return
        heartbeat_at = self._engine.last_heartbeat_at
        self._logger.info(
            self._heartbeat_log_message,
            extra={
                "run_id": self._engine.state.run_id,
                "phase": self._engine.state.phase,
                "last_heartbeat_at": (
                    heartbeat_at.isoformat() if heartbeat_at is not None else None
                ),
                "status": self._engine.state.status,
            },
        )


__all__ = ["SharedJobProgressTrackerBase"]
