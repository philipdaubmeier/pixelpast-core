"""Service composition root for calendar event ingestion."""

from __future__ import annotations

from pathlib import Path

from pixelpast.ingestion.calendar.connector import CalendarConnector
from pixelpast.ingestion.calendar.contracts import CalendarIngestionResult
from pixelpast.ingestion.calendar.lifecycle import CalendarIngestionRunCoordinator
from pixelpast.ingestion.calendar.progress import (
    CalendarIngestionProgressSnapshot,
    CalendarIngestionProgressTracker,
)
from pixelpast.ingestion.calendar.staged import (
    CalendarIngestionPersistenceScope,
    CalendarStagedIngestionStrategy,
)
from pixelpast.ingestion.service_base import SharedStagedIngestionServiceBase
from pixelpast.shared.progress import JobProgressCallback
from pixelpast.shared.runtime import RuntimeContext


class CalendarIngestionService(
    SharedStagedIngestionServiceBase[
        CalendarConnector,
        CalendarIngestionRunCoordinator,
        CalendarStagedIngestionStrategy,
        CalendarIngestionProgressTracker,
        CalendarIngestionPersistenceScope,
        CalendarIngestionResult,
    ]
):
    """Wire calendar-specific collaborators into the staged ingestion runner."""

    def _build_default_connector(self) -> CalendarConnector:
        return CalendarConnector()

    def _build_default_lifecycle(self) -> CalendarIngestionRunCoordinator:
        return CalendarIngestionRunCoordinator()

    def _resolve_runtime_root(
        self,
        *,
        runtime: RuntimeContext,
        **kwargs: object,
    ) -> Path:
        configured_root = kwargs.get("root") or runtime.settings.calendar_root
        if configured_root is None:
            raise ValueError(
                "Calendar ingestion requires PIXELPAST_CALENDAR_ROOT to be configured."
            )
        return configured_root.expanduser().resolve()

    def _build_strategy(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
        **kwargs: object,
    ) -> CalendarStagedIngestionStrategy:
        del runtime, resolved_root, kwargs
        return CalendarStagedIngestionStrategy(connector=self._connector)

    def _build_progress_tracker(
        self,
        *,
        runtime: RuntimeContext,
        run_id: int,
        progress_callback: JobProgressCallback | None,
        **kwargs: object,
    ) -> CalendarIngestionProgressTracker:
        del kwargs
        return CalendarIngestionProgressTracker(
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
    ) -> CalendarIngestionPersistenceScope:
        del resolved_root, kwargs
        return CalendarIngestionPersistenceScope(
            runtime=runtime,
            lifecycle=self._lifecycle,
        )

    def ingest(
        self,
        *,
        runtime: RuntimeContext,
        root: Path | None = None,
        progress_callback: JobProgressCallback | None = None,
    ) -> CalendarIngestionResult:
        """Run staged calendar ingestion and return the stable public result."""

        return self._ingest(
            runtime=runtime,
            root=root,
            progress_callback=progress_callback,
        )


__all__ = [
    "CalendarIngestionProgressSnapshot",
    "CalendarIngestionResult",
    "CalendarIngestionService",
]
