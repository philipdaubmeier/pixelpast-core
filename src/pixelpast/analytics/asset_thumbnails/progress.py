"""Progress reporting for the asset thumbnail derive job."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from pixelpast.shared.job_progress_tracker import SharedJobProgressTrackerBase
from pixelpast.shared.progress import JobProgressCallback, JobProgressSnapshot
from pixelpast.shared.runtime import RuntimeContext

logger = logging.getLogger(__name__)

ASSET_THUMBNAILS_JOB_NAME = "asset-thumbnails"


@dataclass(slots=True)
class AssetThumbnailProgressState:
    """Track thumbnail derivation counters under the shared progress contract."""

    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0
    failed: int = 0

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
            "updated": self.updated,
            "unchanged": self.unchanged,
            "skipped": self.skipped,
            "failed": self.failed,
            "missing_from_source": 0,
        }


class AssetThumbnailProgressTracker(
    SharedJobProgressTrackerBase[AssetThumbnailProgressState]
):
    """Thumbnail-job adapter over the shared progress engine."""

    loading_phase = "loading thumbnail candidates"
    rendering_phase = "rendering thumbnails"

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
            state=AssetThumbnailProgressState(),
            job_type="derive",
            job=ASSET_THUMBNAILS_JOB_NAME,
            run_id=run_id,
            runtime=runtime,
            logger=logger,
            heartbeat_log_message="asset thumbnail derive heartbeat written",
            callback=callback,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
            now_factory=now_factory,
            monotonic_factory=monotonic_factory,
        )

    def start_loading(self) -> None:
        self._start_phase(
            phase=self.loading_phase,
            total=None,
            log_message="asset thumbnail derive phase started",
        )

    def mark_loading_completed(self, *, asset_count: int) -> None:
        self._engine.state.set_phase_progress(
            completed=asset_count,
            total=asset_count,
        )
        self._emit(event="progress", force_persist=True)

    def start_rendering(self, *, total_output_count: int) -> None:
        self._start_phase(
            phase=self.rendering_phase,
            total=total_output_count,
            log_message="asset thumbnail derive phase started",
        )

    def mark_output_result(self, *, status: str) -> None:
        if status == "generated":
            self._state.inserted += 1
        elif status == "overwritten":
            self._state.updated += 1
        elif status == "unchanged":
            self._state.unchanged += 1
        elif status == "skipped":
            self._state.skipped += 1
        elif status == "failed":
            self._state.failed += 1
        else:
            raise ValueError(f"Unsupported thumbnail output status: {status}.")

        self._engine.state.increment_phase_completed()
        self._emit(event="progress", force_persist=True)

    def finish_phase(self) -> None:
        self._finish_phase()

    def finish_run(self, *, status: str) -> JobProgressSnapshot:
        return self._finish_run(
            status=status,
            log_message="asset thumbnail derive completed",
        )

    def fail_run(self) -> JobProgressSnapshot:
        return self._fail_run(log_message="asset thumbnail derive failed")


__all__ = [
    "ASSET_THUMBNAILS_JOB_NAME",
    "AssetThumbnailProgressTracker",
]
