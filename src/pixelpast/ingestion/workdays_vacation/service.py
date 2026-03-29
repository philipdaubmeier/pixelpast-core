"""Service composition root for workdays-vacation ingestion."""

from __future__ import annotations

from pathlib import Path

from pixelpast.ingestion.service_base import SharedStagedIngestionServiceBase
from pixelpast.ingestion.workdays_vacation.connector import WorkdaysVacationConnector
from pixelpast.ingestion.workdays_vacation.contracts import (
    WorkdaysVacationIngestionResult,
)
from pixelpast.ingestion.workdays_vacation.lifecycle import (
    WorkdaysVacationIngestionRunCoordinator,
)
from pixelpast.ingestion.workdays_vacation.progress import (
    WorkdaysVacationIngestionProgressSnapshot,
    WorkdaysVacationIngestionProgressTracker,
)
from pixelpast.ingestion.workdays_vacation.staged import (
    WorkdaysVacationIngestionPersistenceScope,
    WorkdaysVacationStagedIngestionStrategy,
)
from pixelpast.shared.progress import JobProgressCallback
from pixelpast.shared.runtime import RuntimeContext


class WorkdaysVacationIngestionService(
    SharedStagedIngestionServiceBase[
        WorkdaysVacationConnector,
        WorkdaysVacationIngestionRunCoordinator,
        WorkdaysVacationStagedIngestionStrategy,
        WorkdaysVacationIngestionProgressTracker,
        WorkdaysVacationIngestionPersistenceScope,
        WorkdaysVacationIngestionResult,
    ]
):
    """Wire connector-specific collaborators into the staged ingestion runner."""

    def _build_default_connector(self) -> WorkdaysVacationConnector:
        return WorkdaysVacationConnector()

    def _build_default_lifecycle(self) -> WorkdaysVacationIngestionRunCoordinator:
        return WorkdaysVacationIngestionRunCoordinator()

    def _resolve_runtime_root(
        self,
        *,
        runtime: RuntimeContext,
        **kwargs: object,
    ) -> Path:
        configured_root = kwargs.get("root") or runtime.settings.workdays_vacation_root
        if configured_root is None:
            raise ValueError(
                "Workdays vacation ingestion requires "
                "PIXELPAST_WORKDAYS_VACATION_ROOT to be configured."
            )
        return configured_root.expanduser().resolve()

    def _build_strategy(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
        **kwargs: object,
    ) -> WorkdaysVacationStagedIngestionStrategy:
        del runtime, resolved_root, kwargs
        return WorkdaysVacationStagedIngestionStrategy(connector=self._connector)

    def _build_progress_tracker(
        self,
        *,
        runtime: RuntimeContext,
        run_id: int,
        progress_callback: JobProgressCallback | None,
        **kwargs: object,
    ) -> WorkdaysVacationIngestionProgressTracker:
        del kwargs
        return WorkdaysVacationIngestionProgressTracker(
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
    ) -> WorkdaysVacationIngestionPersistenceScope:
        del resolved_root, kwargs
        return WorkdaysVacationIngestionPersistenceScope(
            runtime=runtime,
            lifecycle=self._lifecycle,
        )

    def ingest(
        self,
        *,
        runtime: RuntimeContext,
        root: Path | None = None,
        progress_callback: JobProgressCallback | None = None,
    ) -> WorkdaysVacationIngestionResult:
        """Run staged workdays-vacation ingestion and return the public result."""

        return self._ingest(
            runtime=runtime,
            root=root,
            progress_callback=progress_callback,
        )


__all__ = [
    "WorkdaysVacationIngestionProgressSnapshot",
    "WorkdaysVacationIngestionResult",
    "WorkdaysVacationIngestionService",
]
