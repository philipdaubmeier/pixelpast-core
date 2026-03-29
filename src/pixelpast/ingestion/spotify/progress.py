"""Stable progress import path and runtime adapter for Spotify ingestion."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from pixelpast.ingestion.spotify.contracts import SpotifyTransformError
from pixelpast.ingestion.spotify.fetch import SpotifyDocumentLoadProgress
from pixelpast.ingestion.progress_base import SharedIngestionProgressTrackerBase
from pixelpast.shared.progress import JobProgressCallback, JobProgressSnapshot
from pixelpast.shared.runtime import RuntimeContext

logger = logging.getLogger(__name__)

SpotifyIngestionProgressSnapshot = JobProgressSnapshot


@dataclass(slots=True)
class SpotifyIngestionProgressState:
    """Spotify-specific counters tracked alongside the generic progress snapshot."""

    discovered_file_count: int = 0
    analyzed_file_count: int = 0
    failed: int = 0
    documents_submitted: int = 0
    documents_completed: int = 0
    persisted_source_count: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0
    missing_from_source: int = 0
    persisted_event_count: int = 0

    def apply_discovery_count(self, *, discovered_file_count: int) -> None:
        self.discovered_file_count = discovered_file_count

    def apply_missing_from_source_count(
        self,
        *,
        missing_from_source_count: int,
    ) -> None:
        self.missing_from_source = missing_from_source_count

    def apply_document_load(self, progress: SpotifyDocumentLoadProgress) -> None:
        if progress.event == "submitted":
            self.documents_submitted += 1
        elif progress.event == "completed":
            self.documents_completed += 1

    def mark_analysis_success(self) -> int:
        self.analyzed_file_count += 1
        return self.analysis_completed_count

    def mark_analysis_failure(self) -> int:
        self.failed += 1
        return self.analysis_completed_count

    def mark_persisted(self, *, outcome: str) -> None:
        _normalized_outcome, _event_count, detailed_counts = _parse_account_outcome(outcome)
        self.persisted_source_count += 1
        if detailed_counts is None:
            return
        self.inserted += detailed_counts["inserted"]
        self.updated += detailed_counts["updated"]
        self.unchanged += detailed_counts["unchanged"]
        self.skipped += detailed_counts["skipped"]
        self.persisted_event_count += detailed_counts["persisted_event_count"]

    @property
    def analysis_completed_count(self) -> int:
        return self.analyzed_file_count + self.failed

    def to_progress_payload(
        self,
        *,
        total: int | None,
        completed: int,
    ) -> dict[str, int | str | None]:
        return {
            "total": total,
            "completed": completed,
            "inserted": self.inserted,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "skipped": self.skipped,
            "failed": self.failed,
            "missing_from_source": self.missing_from_source,
            "persisted_event_count": self.persisted_event_count,
        }


class SpotifyIngestionProgressTracker(
    SharedIngestionProgressTrackerBase[
        SpotifyIngestionProgressState,
        SpotifyTransformError,
    ]
):
    """Spotify-specific adapter over the generic ingestion progress engine."""

    analysis_failure_log_message = "spotify ingestion skipped document"

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
            state=SpotifyIngestionProgressState(),
            job="spotify",
            run_id=run_id,
            runtime=runtime,
            logger=logger,
            callback=callback,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
            now_factory=now_factory,
            monotonic_factory=monotonic_factory,
        )

    def mark_metadata_batch(self, progress: SpotifyDocumentLoadProgress) -> None:
        self._state.apply_document_load(progress)
        if progress.event == "completed":
            self._engine.state.set_phase_progress(completed=self._state.documents_completed)
        self._emit(event="progress")

    def _build_analysis_failure_log_extra(
        self,
        *,
        error: SpotifyTransformError,
    ) -> dict[str, object]:
        return {
            "document": error.document.origin_label,
            "reason": error.message,
        }


def _parse_account_outcome(
    outcome: str,
) -> tuple[str, int, dict[str, int] | None]:
    if "=" in outcome and ";" in outcome:
        detailed_counts = {
            key: int(value)
            for key, value in (
                part.split("=", 1) for part in outcome.split(";") if part.strip()
            )
        }
        return (
            "detailed",
            detailed_counts.get("persisted_event_count", 0),
            {
                "inserted": detailed_counts.get("inserted", 0),
                "updated": detailed_counts.get("updated", 0),
                "unchanged": detailed_counts.get("unchanged", 0),
                "skipped": detailed_counts.get("skipped", 0),
                "persisted_event_count": detailed_counts.get(
                    "persisted_event_count",
                    0,
                ),
            },
        )

    normalized_outcome, separator, event_count = outcome.partition(":")
    if not separator:
        return normalized_outcome, 0, None
    return normalized_outcome, int(event_count), None


__all__ = [
    "SpotifyIngestionProgressSnapshot",
    "SpotifyIngestionProgressTracker",
]
