"""Service composition root for Google Maps Timeline event ingestion."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from time import monotonic

from pixelpast.ingestion.google_maps_timeline.connector import (
    GoogleMapsTimelineConnector,
)
from pixelpast.ingestion.google_maps_timeline.contracts import (
    GoogleMapsTimelineIngestionResult,
)
from pixelpast.ingestion.google_maps_timeline.discovery import (
    resolve_google_maps_timeline_ingestion_root,
)
from pixelpast.ingestion.google_maps_timeline.lifecycle import (
    GoogleMapsTimelineIngestionRunCoordinator,
)
from pixelpast.ingestion.google_maps_timeline.progress import (
    GoogleMapsTimelineIngestionProgressSnapshot,
    GoogleMapsTimelineIngestionProgressTracker,
)
from pixelpast.ingestion.google_maps_timeline.staged import (
    GoogleMapsTimelineIngestionPersistenceScope,
    GoogleMapsTimelineStagedIngestionStrategy,
)
from pixelpast.ingestion.staged import StagedIngestionRunner
from pixelpast.shared.progress import JobProgressCallback
from pixelpast.shared.runtime import RuntimeContext

_HEARTBEAT_INTERVAL_SECONDS = 10.0


class GoogleMapsTimelineIngestionService:
    """Wire Google Maps Timeline collaborators into the staged runner."""

    def __init__(
        self,
        connector: GoogleMapsTimelineConnector | None = None,
        lifecycle: GoogleMapsTimelineIngestionRunCoordinator | None = None,
        *,
        heartbeat_interval_seconds: float = _HEARTBEAT_INTERVAL_SECONDS,
        now_factory: Callable[[], datetime] | None = None,
        monotonic_factory: Callable[[], float] | None = None,
    ) -> None:
        self._connector = connector or GoogleMapsTimelineConnector()
        self._lifecycle = lifecycle or GoogleMapsTimelineIngestionRunCoordinator()
        self._heartbeat_interval_seconds = heartbeat_interval_seconds
        self._now_factory = now_factory
        self._monotonic_factory = monotonic_factory or monotonic
        self._runner = StagedIngestionRunner(
            strategy=GoogleMapsTimelineStagedIngestionStrategy(
                connector=self._connector
            )
        )

    def ingest(
        self,
        *,
        runtime: RuntimeContext,
        root: Path | None = None,
        progress_callback: JobProgressCallback | None = None,
    ) -> GoogleMapsTimelineIngestionResult:
        """Run staged Google Maps Timeline ingestion and return the result."""

        resolved_root = resolve_google_maps_timeline_ingestion_root(
            settings=runtime.settings,
            root=root,
        )
        run_id = self._lifecycle.create_run(
            runtime=runtime,
            resolved_root=resolved_root,
        )
        progress = GoogleMapsTimelineIngestionProgressTracker(
            run_id=run_id,
            runtime=runtime,
            callback=progress_callback,
            heartbeat_interval_seconds=self._heartbeat_interval_seconds,
            now_factory=self._now_factory,
            monotonic_factory=self._monotonic_factory,
        )
        persistence = GoogleMapsTimelineIngestionPersistenceScope(
            runtime=runtime,
            lifecycle=self._lifecycle,
        )
        result = self._runner.run(
            resolved_root=resolved_root,
            run_id=run_id,
            progress=progress,
            persistence=persistence,
        )
        if result.persisted_source_count == 0 and result.transform_errors:
            raise ValueError(result.transform_errors[0].message)
        return result


__all__ = [
    "GoogleMapsTimelineIngestionProgressSnapshot",
    "GoogleMapsTimelineIngestionResult",
    "GoogleMapsTimelineIngestionService",
]
