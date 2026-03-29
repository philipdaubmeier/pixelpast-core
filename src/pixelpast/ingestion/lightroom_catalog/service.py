"""Service composition root for Lightroom catalog ingestion."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from time import monotonic

from pixelpast.ingestion.lightroom_catalog.connector import LightroomCatalogConnector
from pixelpast.ingestion.lightroom_catalog.contracts import LightroomIngestionResult
from pixelpast.ingestion.lightroom_catalog.progress import (
    LightroomCatalogIngestionProgressSnapshot,
    LightroomCatalogIngestionProgressTracker,
)
from pixelpast.ingestion.lightroom_catalog.lifecycle import (
    LightroomCatalogIngestionRunCoordinator,
)
from pixelpast.ingestion.lightroom_catalog.staged import (
    LightroomCatalogIngestionPersistenceScope,
    LightroomCatalogStagedIngestionStrategy,
)
from pixelpast.ingestion.staged import StagedIngestionRunner
from pixelpast.shared.progress import JobProgressCallback
from pixelpast.shared.runtime import RuntimeContext

_HEARTBEAT_INTERVAL_SECONDS = 10.0


class LightroomCatalogIngestionService:
    """Wire Lightroom-specific collaborators into the staged ingestion runner."""

    def __init__(
        self,
        connector: LightroomCatalogConnector | None = None,
        lifecycle: LightroomCatalogIngestionRunCoordinator | None = None,
        *,
        heartbeat_interval_seconds: float = _HEARTBEAT_INTERVAL_SECONDS,
        now_factory: Callable[[], datetime] | None = None,
        monotonic_factory: Callable[[], float] | None = None,
    ) -> None:
        self._connector = connector or LightroomCatalogConnector()
        self._lifecycle = lifecycle or LightroomCatalogIngestionRunCoordinator()
        self._heartbeat_interval_seconds = heartbeat_interval_seconds
        self._now_factory = now_factory
        self._monotonic_factory = monotonic_factory or monotonic

    def ingest(
        self,
        *,
        runtime: RuntimeContext,
        root: Path | None = None,
        start_index: int | None = None,
        end_index: int | None = None,
        progress_callback: JobProgressCallback | None = None,
    ) -> LightroomIngestionResult:
        """Run staged Lightroom catalog ingestion and return the public result."""

        configured_root = root or runtime.settings.lightroom_catalog_path
        if configured_root is None:
            raise ValueError(
                "Lightroom catalog ingestion requires "
                "PIXELPAST_LIGHTROOM_CATALOG_PATH to be configured."
            )

        resolved_root = configured_root.expanduser().resolve()
        if start_index is not None and end_index is not None and start_index > end_index:
            raise ValueError(
                "Lightroom asset range start index must be less than or equal to the end index."
            )

        run_id = self._lifecycle.create_run(
            runtime=runtime,
            resolved_root=resolved_root,
        )
        progress = LightroomCatalogIngestionProgressTracker(
            run_id=run_id,
            runtime=runtime,
            callback=progress_callback,
            heartbeat_interval_seconds=self._heartbeat_interval_seconds,
            now_factory=self._now_factory,
            monotonic_factory=self._monotonic_factory,
        )
        persistence = LightroomCatalogIngestionPersistenceScope(
            runtime=runtime,
            lifecycle=self._lifecycle,
        )
        runner = StagedIngestionRunner(
            strategy=LightroomCatalogStagedIngestionStrategy(
                connector=self._connector,
                start_index=start_index,
                end_index=end_index,
            )
        )
        return runner.run(
            resolved_root=resolved_root,
            run_id=run_id,
            progress=progress,
            persistence=persistence,
        )


__all__ = [
    "LightroomCatalogIngestionProgressSnapshot",
    "LightroomCatalogIngestionService",
    "LightroomIngestionResult",
]
