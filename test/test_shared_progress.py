"""Tests for shared job progress behavior."""

from __future__ import annotations

from sqlalchemy.exc import OperationalError

from pixelpast.shared.progress import JobProgressEngine, JobProgressSnapshot


def test_job_progress_engine_tolerates_sqlite_lock_for_non_terminal_heartbeat() -> None:
    snapshots: list[JobProgressSnapshot] = []
    engine = JobProgressEngine(
        job_type="derive",
        job="google_places",
        run_id=7,
        runtime=object(),  # type: ignore[arg-type]
        payload_factory=lambda: {
            "total": 5,
            "completed": 3,
            "inserted": 0,
            "updated": 0,
            "unchanged": 0,
            "skipped": 0,
            "failed": 0,
            "missing_from_source": 0,
        },
        snapshot_factory=lambda event, heartbeat_written: JobProgressSnapshot(
            event=event,
            job_type="derive",
            job="google_places",
            run_id=7,
            phase="collecting place ids",
            status="running",
            total=5,
            completed=3,
            inserted=0,
            updated=0,
            unchanged=0,
            skipped=0,
            failed=0,
            missing_from_source=0,
            heartbeat_written=heartbeat_written,
        ),
        callback=snapshots.append,
    )

    def raise_locked_error(*, persist):
        raise OperationalError(
            statement="UPDATE job_run SET progress_json = ?",
            params={},
            orig=Exception("database is locked"),
        )

    engine._persist_job_run = raise_locked_error  # type: ignore[method-assign]
    snapshot = engine.emit(event="progress", force_persist=True)

    assert snapshot.heartbeat_written is False
    assert snapshots == [snapshot]
