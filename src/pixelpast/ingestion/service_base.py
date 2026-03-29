"""Shared template base for staged ingestion service composition roots."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from time import monotonic
from typing import Any, Generic, TypeVar

from pixelpast.ingestion.staged import StagedIngestionRunner
from pixelpast.shared.progress import JobProgressCallback
from pixelpast.shared.runtime import RuntimeContext

ConnectorT = TypeVar("ConnectorT")
LifecycleT = TypeVar("LifecycleT")
StrategyT = TypeVar("StrategyT")
ProgressT = TypeVar("ProgressT")
PersistenceT = TypeVar("PersistenceT")
ResultT = TypeVar("ResultT")


class SharedStagedIngestionServiceBase(
    Generic[
        ConnectorT,
        LifecycleT,
        StrategyT,
        ProgressT,
        PersistenceT,
        ResultT,
    ]
):
    """Centralize the staged-ingestion service orchestration shell."""

    def __init__(
        self,
        connector: ConnectorT | None = None,
        lifecycle: LifecycleT | None = None,
        *,
        heartbeat_interval_seconds: float = 10.0,
        now_factory: Callable[[], datetime] | None = None,
        monotonic_factory: Callable[[], float] | None = None,
    ) -> None:
        self._connector = connector or self._build_default_connector()
        self._lifecycle = lifecycle or self._build_default_lifecycle()
        self._heartbeat_interval_seconds = heartbeat_interval_seconds
        self._now_factory = now_factory
        self._monotonic_factory = monotonic_factory or monotonic

    def _ingest(
        self,
        *,
        runtime: RuntimeContext,
        progress_callback: JobProgressCallback | None = None,
        **kwargs: Any,
    ) -> ResultT:
        """Run one staged ingestion execution through shared service wiring."""

        resolved_root = self._resolve_runtime_root(runtime=runtime, **kwargs)
        self._validate_request(
            runtime=runtime,
            resolved_root=resolved_root,
            **kwargs,
        )
        run_id = self._lifecycle.create_run(
            runtime=runtime,
            resolved_root=resolved_root,
        )
        progress = self._build_progress_tracker(
            runtime=runtime,
            run_id=run_id,
            progress_callback=progress_callback,
            **kwargs,
        )
        persistence = self._build_persistence_scope(
            runtime=runtime,
            resolved_root=resolved_root,
            **kwargs,
        )
        result = self._build_runner(
            strategy=self._build_strategy(
                runtime=runtime,
                resolved_root=resolved_root,
                **kwargs,
            )
        ).run(
            resolved_root=resolved_root,
            run_id=run_id,
            progress=progress,
            persistence=persistence,
        )
        return self._post_process_result(
            runtime=runtime,
            resolved_root=resolved_root,
            result=result,
            **kwargs,
        )

    def _build_runner(self, *, strategy: StrategyT) -> StagedIngestionRunner:
        return StagedIngestionRunner(strategy=strategy)

    def _validate_request(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
        **kwargs: Any,
    ) -> None:
        del runtime, resolved_root, kwargs

    def _post_process_result(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
        result: ResultT,
        **kwargs: Any,
    ) -> ResultT:
        del runtime, resolved_root, kwargs
        return result

    def _build_default_connector(self) -> ConnectorT:
        raise NotImplementedError

    def _build_default_lifecycle(self) -> LifecycleT:
        raise NotImplementedError

    def _resolve_runtime_root(
        self,
        *,
        runtime: RuntimeContext,
        **kwargs: Any,
    ) -> Path:
        raise NotImplementedError

    def _build_strategy(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
        **kwargs: Any,
    ) -> StrategyT:
        raise NotImplementedError

    def _build_progress_tracker(
        self,
        *,
        runtime: RuntimeContext,
        run_id: int,
        progress_callback: JobProgressCallback | None,
        **kwargs: Any,
    ) -> ProgressT:
        raise NotImplementedError

    def _build_persistence_scope(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
        **kwargs: Any,
    ) -> PersistenceT:
        raise NotImplementedError


__all__ = ["SharedStagedIngestionServiceBase"]
