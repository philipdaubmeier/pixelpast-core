"""Service composition root for Google Maps Timeline event ingestion."""

from __future__ import annotations

from pathlib import Path

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
from pixelpast.ingestion.service_base import SharedStagedIngestionServiceBase
from pixelpast.shared.progress import JobProgressCallback
from pixelpast.shared.runtime import RuntimeContext


class GoogleMapsTimelineIngestionService(
    SharedStagedIngestionServiceBase[
        GoogleMapsTimelineConnector,
        GoogleMapsTimelineIngestionRunCoordinator,
        GoogleMapsTimelineStagedIngestionStrategy,
        GoogleMapsTimelineIngestionProgressTracker,
        GoogleMapsTimelineIngestionPersistenceScope,
        GoogleMapsTimelineIngestionResult,
    ]
):
    """Wire Google Maps Timeline collaborators into the staged runner."""

    def _build_default_connector(self) -> GoogleMapsTimelineConnector:
        return GoogleMapsTimelineConnector()

    def _build_default_lifecycle(self) -> GoogleMapsTimelineIngestionRunCoordinator:
        return GoogleMapsTimelineIngestionRunCoordinator()

    def _resolve_runtime_root(
        self,
        *,
        runtime: RuntimeContext,
        **kwargs: object,
    ) -> Path:
        root = kwargs.get("root")
        return resolve_google_maps_timeline_ingestion_root(
            settings=runtime.settings,
            root=root,
        )

    def _build_strategy(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
        **kwargs: object,
    ) -> GoogleMapsTimelineStagedIngestionStrategy:
        del runtime, resolved_root, kwargs
        return GoogleMapsTimelineStagedIngestionStrategy(connector=self._connector)

    def _build_progress_tracker(
        self,
        *,
        runtime: RuntimeContext,
        run_id: int,
        progress_callback: JobProgressCallback | None,
        **kwargs: object,
    ) -> GoogleMapsTimelineIngestionProgressTracker:
        del kwargs
        return GoogleMapsTimelineIngestionProgressTracker(
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
    ) -> GoogleMapsTimelineIngestionPersistenceScope:
        del resolved_root, kwargs
        return GoogleMapsTimelineIngestionPersistenceScope(
            runtime=runtime,
            lifecycle=self._lifecycle,
        )

    def _post_process_result(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
        result: GoogleMapsTimelineIngestionResult,
        **kwargs: object,
    ) -> GoogleMapsTimelineIngestionResult:
        del runtime, resolved_root, kwargs
        if result.persisted_source_count == 0 and result.transform_errors:
            raise ValueError(result.transform_errors[0].message)
        return result

    def ingest(
        self,
        *,
        runtime: RuntimeContext,
        root: Path | None = None,
        progress_callback: JobProgressCallback | None = None,
    ) -> GoogleMapsTimelineIngestionResult:
        """Run staged Google Maps Timeline ingestion and return the result."""

        return self._ingest(
            runtime=runtime,
            root=root,
            progress_callback=progress_callback,
        )


__all__ = [
    "GoogleMapsTimelineIngestionProgressSnapshot",
    "GoogleMapsTimelineIngestionResult",
    "GoogleMapsTimelineIngestionService",
]
