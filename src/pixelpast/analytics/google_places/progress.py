"""Progress reporting for the Google Places derive job."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from pixelpast.shared.job_progress_tracker import SharedJobProgressTrackerBase
from pixelpast.shared.progress import JobProgressCallback, JobProgressSnapshot
from pixelpast.shared.runtime import RuntimeContext

logger = logging.getLogger(__name__)

GOOGLE_PLACES_JOB_NAME = "google_places"


@dataclass(slots=True)
class GooglePlacesProgressState:
    """Track Google Places job counters within the shared progress contract."""

    scanned_event_count: int = 0
    candidate_event_count: int = 0
    unique_place_id_count: int = 0
    remote_fetch_count: int = 0
    cached_reuse_count: int = 0
    inserted_place_count: int = 0
    updated_place_count: int = 0
    unchanged_place_count: int = 0
    inserted_event_place_link_count: int = 0
    updated_event_place_link_count: int = 0
    unchanged_event_place_link_count: int = 0
    skipped_place_count: int = 0
    failed: int = 0

    def to_progress_payload(
        self,
        *,
        total: int | None,
        completed: int,
    ) -> dict[str, int | None]:
        """Render the persisted shared progress payload for the active phase."""

        return {
            "total": total,
            "completed": completed,
            "inserted": self.inserted_place_count,
            "updated": self.updated_place_count,
            "unchanged": self.unchanged_place_count,
            "skipped": self.skipped_place_count,
            "failed": self.failed,
            "missing_from_source": 0,
        }


class GooglePlacesProgressTracker(
    SharedJobProgressTrackerBase[GooglePlacesProgressState]
):
    """Google-Places-specific adapter over the shared job progress engine."""

    collecting_phase = "collecting place ids"
    fetching_phase = "fetching place details"
    persisting_phase = "persisting places and links"

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
            state=GooglePlacesProgressState(),
            job_type="derive",
            job=GOOGLE_PLACES_JOB_NAME,
            run_id=run_id,
            runtime=runtime,
            logger=logger,
            heartbeat_log_message="google places derive heartbeat written",
            callback=callback,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
            now_factory=now_factory,
            monotonic_factory=monotonic_factory,
        )

    def start_collecting(self) -> None:
        """Enter canonical candidate loading."""

        self._start_phase(
            phase=self.collecting_phase,
            total=None,
            log_message="google places derive phase started",
        )

    def mark_collecting_completed(
        self,
        *,
        scanned_event_count: int,
        candidate_event_count: int,
        unique_place_id_count: int,
        cached_reuse_count: int,
    ) -> None:
        """Persist collection totals once canonical loading is complete."""

        self._state.scanned_event_count = scanned_event_count
        self._state.candidate_event_count = candidate_event_count
        self._state.unique_place_id_count = unique_place_id_count
        self._state.cached_reuse_count = cached_reuse_count
        self._engine.state.set_phase_progress(
            completed=scanned_event_count,
            total=scanned_event_count,
        )
        self._emit(event="progress", force_persist=True)

    def start_fetching(self, *, total_place_count: int) -> None:
        """Enter provider fetch execution."""

        self._start_phase(
            phase=self.fetching_phase,
            total=total_place_count,
            log_message="google places derive phase started",
        )

    def mark_place_fetched(self) -> None:
        """Record one completed remote place fetch."""

        self._state.remote_fetch_count += 1
        self._engine.state.increment_phase_completed()
        self._emit(event="progress", force_persist=True)

    def mark_place_skipped(self) -> None:
        """Record one skipped place id during provider fetch recovery."""

        self._state.skipped_place_count += 1
        self._engine.state.increment_phase_completed()
        self._emit(event="progress", force_persist=True)

    def start_persisting(self, *, total_write_count: int) -> None:
        """Enter place and event-place persistence."""

        self._start_phase(
            phase=self.persisting_phase,
            total=total_write_count,
            log_message="google places derive phase started",
        )

    def mark_persisted(
        self,
        *,
        place_write_count: int,
        link_write_count: int,
        inserted_place_count: int,
        updated_place_count: int,
        unchanged_place_count: int,
        inserted_event_place_link_count: int,
        updated_event_place_link_count: int,
        unchanged_event_place_link_count: int,
    ) -> None:
        """Persist place-cache and event-link outcome counters."""

        self._state.inserted_place_count = inserted_place_count
        self._state.updated_place_count = updated_place_count
        self._state.unchanged_place_count = unchanged_place_count
        self._state.inserted_event_place_link_count = inserted_event_place_link_count
        self._state.updated_event_place_link_count = updated_event_place_link_count
        self._state.unchanged_event_place_link_count = (
            unchanged_event_place_link_count
        )
        completed = place_write_count + link_write_count
        self._engine.state.set_phase_progress(
            completed=completed,
            total=completed,
        )
        self._emit(event="progress", force_persist=True)

    def mark_failed_operation(self) -> None:
        """Increment the shared failed counter for a hard job failure."""

        self._state.failed += 1

    def finish_phase(self) -> None:
        """Persist completion of the active derive phase."""

        self._finish_phase()

    def finish_run(self, *, status: str) -> JobProgressSnapshot:
        """Persist a terminal successful derive state."""

        return self._finish_run(
            status=status,
            log_message="google places derive completed",
        )

    def fail_run(self) -> JobProgressSnapshot:
        """Persist a terminal failed derive state."""

        return self._fail_run(log_message="google places derive failed")


__all__ = [
    "GOOGLE_PLACES_JOB_NAME",
    "GooglePlacesProgressTracker",
]
