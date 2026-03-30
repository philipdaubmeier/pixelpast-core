"""Service composition root for photo asset ingestion."""

from __future__ import annotations

from pathlib import Path

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
from pixelpast.ingestion.service_base import SharedStagedIngestionServiceBase
from pixelpast.shared.media_storage import require_media_thumb_root
from pixelpast.shared.progress import JobProgressCallback
from pixelpast.shared.runtime import RuntimeContext


class PhotoIngestionService(
    SharedStagedIngestionServiceBase[
        PhotoConnector,
        PhotoIngestionRunCoordinator,
        PhotoStagedIngestionStrategy,
        PhotoIngestionProgressTracker,
        PhotoIngestionPersistenceScope,
        PhotoIngestionResult,
    ]
):
    """Wire photo-specific collaborators into the staged ingestion runner."""

    def _build_default_connector(self) -> PhotoConnector:
        return PhotoConnector()

    def _build_default_lifecycle(self) -> PhotoIngestionRunCoordinator:
        return PhotoIngestionRunCoordinator()

    def _resolve_runtime_root(
        self,
        *,
        runtime: RuntimeContext,
        **kwargs: object,
    ) -> Path:
        del kwargs
        photos_root = runtime.settings.photos_root
        if photos_root is None:
            raise ValueError(
                "Photo ingestion requires PIXELPAST_PHOTOS_ROOT to be configured."
            )
        return photos_root.expanduser().resolve()

    def _build_strategy(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
        **kwargs: object,
    ) -> PhotoStagedIngestionStrategy:
        del runtime, resolved_root, kwargs
        return PhotoStagedIngestionStrategy(connector=self._connector)

    def _validate_request(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
        **kwargs: object,
    ) -> None:
        del resolved_root, kwargs
        require_media_thumb_root(settings=runtime.settings)

    def _build_progress_tracker(
        self,
        *,
        runtime: RuntimeContext,
        run_id: int,
        progress_callback: JobProgressCallback | None,
        **kwargs: object,
    ) -> PhotoIngestionProgressTracker:
        del kwargs
        return PhotoIngestionProgressTracker(
            run_id=run_id,
            runtime=runtime,
            callback=progress_callback,
            heartbeat_interval_seconds=self._heartbeat_interval_seconds,
            now_factory=self._now_factory,
            monotonic_factory=self._monotonic_factory,
        )

    def _build_persistence_scope(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
        **kwargs: object,
    ) -> PhotoIngestionPersistenceScope:
        del kwargs
        return PhotoIngestionPersistenceScope(
            runtime=runtime,
            lifecycle=self._lifecycle,
            resolved_root=resolved_root,
        )

    def ingest(
        self,
        *,
        runtime: RuntimeContext,
        progress_callback: JobProgressCallback | None = None,
    ) -> PhotoIngestionResult:
        """Run staged photo ingestion and return the stable public result."""

        return self._ingest(
            runtime=runtime,
            progress_callback=progress_callback,
        )


__all__ = [
    "PhotoIngestionProgressSnapshot",
    "PhotoIngestionResult",
    "PhotoIngestionService",
]
