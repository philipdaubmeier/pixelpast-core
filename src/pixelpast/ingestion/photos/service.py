"""Service composition root for photo asset ingestion."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from time import monotonic

from pixelpast.ingestion.photos.connector import PhotoConnector
from pixelpast.ingestion.photos.contracts import PhotoIngestionResult
from pixelpast.ingestion.photos.lifecycle import PhotoIngestionRunCoordinator
from pixelpast.ingestion.photos.progress import (
    PhotoIngestionProgressSnapshot,
    PhotoIngestionProgressTracker,
)
from pixelpast.ingestion.photos.staged import (
    PhotoIngestionPersistenceScope,
    PhotoStagedIngestionStrategy,
)
from pixelpast.ingestion.staged import StagedIngestionRunner
from pixelpast.shared.progress import JobProgressCallback
from pixelpast.shared.runtime import RuntimeContext

_HEARTBEAT_INTERVAL_SECONDS = 10.0


class PhotoIngestionService:
    """Wire photo-specific collaborators into the staged ingestion runner."""

    def __init__(
        self,
        connector: PhotoConnector | None = None,
        lifecycle: PhotoIngestionRunCoordinator | None = None,
        *,
        heartbeat_interval_seconds: float = _HEARTBEAT_INTERVAL_SECONDS,
        now_factory: Callable[[], datetime] | None = None,
        monotonic_factory: Callable[[], float] | None = None,
    ) -> None:
        self._connector = connector or PhotoConnector()
        self._lifecycle = lifecycle or PhotoIngestionRunCoordinator()
        self._heartbeat_interval_seconds = heartbeat_interval_seconds
        self._now_factory = now_factory
        self._monotonic_factory = monotonic_factory or monotonic
        self._runner = StagedIngestionRunner(
            strategy=PhotoStagedIngestionStrategy(connector=self._connector)
        )

    def ingest(
        self,
        *,
        runtime: RuntimeContext,
        progress_callback: JobProgressCallback | None = None,
    ) -> PhotoIngestionResult:
        """Run staged photo ingestion and return the stable public result."""

        photos_root = runtime.settings.photos_root
        if photos_root is None:
            raise ValueError(
                "Photo ingestion requires PIXELPAST_PHOTOS_ROOT to be configured."
            )

        resolved_root = photos_root.expanduser().resolve()
        run_id = self._lifecycle.create_run(
            runtime=runtime,
            resolved_root=resolved_root,
        )
        progress = PhotoIngestionProgressTracker(
            run_id=run_id,
            runtime=runtime,
            callback=progress_callback,
            heartbeat_interval_seconds=self._heartbeat_interval_seconds,
            now_factory=self._now_factory,
            monotonic_factory=self._monotonic_factory,
        )
        persistence = PhotoIngestionPersistenceScope(
            runtime=runtime,
            lifecycle=self._lifecycle,
        )
        return self._runner.run(
            resolved_root=resolved_root,
            run_id=run_id,
            progress=progress,
            persistence=persistence,
        )


__all__ = [
    "PhotoIngestionProgressSnapshot",
    "PhotoIngestionResult",
    "PhotoIngestionService",
]
