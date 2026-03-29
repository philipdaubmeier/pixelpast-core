"""Service composition root for Lightroom catalog ingestion."""

from __future__ import annotations

from pathlib import Path

from pixelpast.ingestion.lightroom_catalog.connector import LightroomCatalogConnector
from pixelpast.ingestion.lightroom_catalog.contracts import LightroomIngestionResult
from pixelpast.ingestion.lightroom_catalog.lifecycle import (
    LightroomCatalogIngestionRunCoordinator,
)
from pixelpast.ingestion.lightroom_catalog.progress import (
    LightroomCatalogIngestionProgressSnapshot,
    LightroomCatalogIngestionProgressTracker,
)
from pixelpast.ingestion.lightroom_catalog.staged import (
    LightroomCatalogIngestionPersistenceScope,
    LightroomCatalogStagedIngestionStrategy,
)
from pixelpast.ingestion.service_base import SharedStagedIngestionServiceBase
from pixelpast.shared.progress import JobProgressCallback
from pixelpast.shared.runtime import RuntimeContext


class LightroomCatalogIngestionService(
    SharedStagedIngestionServiceBase[
        LightroomCatalogConnector,
        LightroomCatalogIngestionRunCoordinator,
        LightroomCatalogStagedIngestionStrategy,
        LightroomCatalogIngestionProgressTracker,
        LightroomCatalogIngestionPersistenceScope,
        LightroomIngestionResult,
    ]
):
    """Wire Lightroom-specific collaborators into the staged ingestion runner."""

    def _build_default_connector(self) -> LightroomCatalogConnector:
        return LightroomCatalogConnector()

    def _build_default_lifecycle(self) -> LightroomCatalogIngestionRunCoordinator:
        return LightroomCatalogIngestionRunCoordinator()

    def _resolve_runtime_root(
        self,
        *,
        runtime: RuntimeContext,
        **kwargs: object,
    ) -> Path:
        configured_root = kwargs.get("root") or runtime.settings.lightroom_catalog_path
        if configured_root is None:
            raise ValueError(
                "Lightroom catalog ingestion requires "
                "PIXELPAST_LIGHTROOM_CATALOG_PATH to be configured."
            )
        return configured_root.expanduser().resolve()

    def _validate_request(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
        **kwargs: object,
    ) -> None:
        del runtime, resolved_root
        start_index = kwargs.get("start_index")
        end_index = kwargs.get("end_index")
        if (
            isinstance(start_index, int)
            and isinstance(end_index, int)
            and start_index > end_index
        ):
            raise ValueError(
                "Lightroom asset range start index must be less than or equal to the end index."
            )

    def _build_strategy(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
        **kwargs: object,
    ) -> LightroomCatalogStagedIngestionStrategy:
        del runtime, resolved_root
        return LightroomCatalogStagedIngestionStrategy(
            connector=self._connector,
            start_index=kwargs.get("start_index"),
            end_index=kwargs.get("end_index"),
        )

    def _build_progress_tracker(
        self,
        *,
        runtime: RuntimeContext,
        run_id: int,
        progress_callback: JobProgressCallback | None,
        **kwargs: object,
    ) -> LightroomCatalogIngestionProgressTracker:
        del kwargs
        return LightroomCatalogIngestionProgressTracker(
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
    ) -> LightroomCatalogIngestionPersistenceScope:
        del kwargs
        return LightroomCatalogIngestionPersistenceScope(
            runtime=runtime,
            lifecycle=self._lifecycle,
            resolved_root=resolved_root,
        )

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

        return self._ingest(
            runtime=runtime,
            root=root,
            start_index=start_index,
            end_index=end_index,
            progress_callback=progress_callback,
        )


__all__ = [
    "LightroomCatalogIngestionProgressSnapshot",
    "LightroomCatalogIngestionService",
    "LightroomIngestionResult",
]
