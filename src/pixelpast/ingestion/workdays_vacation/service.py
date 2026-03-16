"""Service composition root for workdays-vacation ingestion."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from time import monotonic

from pixelpast.ingestion.staged import StagedIngestionRunner
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

_HEARTBEAT_INTERVAL_SECONDS = 10.0


class WorkdaysVacationIngestionService:
    """Wire connector-specific collaborators into the staged ingestion runner."""

    def __init__(
        self,
        connector: WorkdaysVacationConnector | None = None,
        lifecycle: WorkdaysVacationIngestionRunCoordinator | None = None,
        *,
        heartbeat_interval_seconds: float = _HEARTBEAT_INTERVAL_SECONDS,
        now_factory: Callable[[], datetime] | None = None,
        monotonic_factory: Callable[[], float] | None = None,
    ) -> None:
        self._connector = connector or WorkdaysVacationConnector()
        self._lifecycle = lifecycle or WorkdaysVacationIngestionRunCoordinator()
        self._heartbeat_interval_seconds = heartbeat_interval_seconds
        self._now_factory = now_factory
        self._monotonic_factory = monotonic_factory or monotonic
        self._runner = StagedIngestionRunner(
            strategy=WorkdaysVacationStagedIngestionStrategy(
                connector=self._connector
            )
        )

    def ingest(
        self,
        *,
        runtime: RuntimeContext,
        root: Path | None = None,
        progress_callback: JobProgressCallback | None = None,
    ) -> WorkdaysVacationIngestionResult:
        """Run staged workdays-vacation ingestion and return the public result."""

        configured_root = root or runtime.settings.workdays_vacation_root
        if configured_root is None:
            raise ValueError(
                "Workdays vacation ingestion requires "
                "PIXELPAST_WORKDAYS_VACATION_ROOT to be configured."
            )

        resolved_root = configured_root.expanduser().resolve()
        run_id = self._lifecycle.create_run(
            runtime=runtime,
            resolved_root=resolved_root,
        )
        progress = WorkdaysVacationIngestionProgressTracker(
            run_id=run_id,
            runtime=runtime,
            callback=progress_callback,
            heartbeat_interval_seconds=self._heartbeat_interval_seconds,
            now_factory=self._now_factory,
            monotonic_factory=self._monotonic_factory,
        )
        persistence = WorkdaysVacationIngestionPersistenceScope(
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
    "WorkdaysVacationIngestionProgressSnapshot",
    "WorkdaysVacationIngestionResult",
    "WorkdaysVacationIngestionService",
]
