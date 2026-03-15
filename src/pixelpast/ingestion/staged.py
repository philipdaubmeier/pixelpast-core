"""Reusable staged runner for file-style ingestion connectors."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, Protocol, TypeVar

DiscoveredUnitT = TypeVar("DiscoveredUnitT")
FetchedPayloadT = TypeVar("FetchedPayloadT")
BatchProgressT = TypeVar("BatchProgressT")
CandidateT = TypeVar("CandidateT")
TransformErrorT = TypeVar("TransformErrorT")
ProgressT = TypeVar("ProgressT", bound="StagedIngestionProgress")
PersistenceScopeT = TypeVar(
    "PersistenceScopeT",
    bound="StagedIngestionPersistenceScope",
)
ResultT = TypeVar("ResultT")


@dataclass(slots=True, frozen=True)
class StagedIngestionPhases:
    """Human-readable phase names for staged ingestion jobs."""

    discovery: str = "filesystem discovery"
    fetch_transform: str = "metadata extraction"
    persistence: str = "canonical persistence"


class StagedIngestionProgress(Protocol[BatchProgressT, TransformErrorT]):
    """Progress tracker contract required by the staged runner."""

    counters: object

    def start_phase(self, *, phase: str, total: int | None) -> None: ...

    def finish_phase(self) -> None: ...

    def mark_discovered(self, *, path: str, discovered_file_count: int) -> None: ...

    def mark_missing_from_source(self, *, missing_from_source_count: int) -> None: ...

    def mark_metadata_batch(self, progress: BatchProgressT) -> None: ...

    def mark_analysis_success(self) -> None: ...

    def mark_analysis_failure(self, *, error: TransformErrorT) -> None: ...

    def mark_persisted(self, *, outcome: str) -> None: ...

    def finish_run(self, *, status: str) -> object: ...

    def fail_run(self) -> object: ...


class StagedIngestionPersistenceScope(Protocol[DiscoveredUnitT, CandidateT]):
    """Persistence contract required by the staged runner."""

    def count_missing_from_source(
        self,
        *,
        resolved_root: Path,
        discovered_units: Sequence[DiscoveredUnitT],
        candidates: Sequence[CandidateT],
    ) -> int: ...

    def persist(self, *, candidate: CandidateT) -> str: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def close(self) -> None: ...


class StagedIngestionStrategy(
    Protocol[
        DiscoveredUnitT,
        FetchedPayloadT,
        BatchProgressT,
        CandidateT,
        TransformErrorT,
        ProgressT,
        ResultT,
    ]
):
    """Connector-specific stage behavior plugged into the generic runner."""

    def discover_units(
        self,
        *,
        root: Path,
        on_unit_discovered,
    ) -> Sequence[DiscoveredUnitT]: ...

    def fetch_payloads(
        self,
        *,
        units: Sequence[DiscoveredUnitT],
        on_batch_progress,
    ) -> FetchedPayloadT: ...

    def build_candidate(
        self,
        *,
        root: Path,
        unit: DiscoveredUnitT,
        fetched_payloads: FetchedPayloadT,
    ) -> CandidateT: ...

    def build_transform_error(
        self,
        *,
        unit: DiscoveredUnitT,
        error: Exception,
    ) -> TransformErrorT: ...

    def describe_unit(self, *, unit: DiscoveredUnitT) -> str: ...

    def build_result(
        self,
        *,
        run_id: int,
        progress: ProgressT,
        transform_errors: Sequence[TransformErrorT],
    ) -> ResultT: ...


class StagedIngestionRunner(
    Generic[
        DiscoveredUnitT,
        FetchedPayloadT,
        BatchProgressT,
        CandidateT,
        TransformErrorT,
        ProgressT,
        PersistenceScopeT,
        ResultT,
    ]
):
    """Own the reusable discover/fetch/transform/persist control flow."""

    def __init__(
        self,
        *,
        strategy: StagedIngestionStrategy[
            DiscoveredUnitT,
            FetchedPayloadT,
            BatchProgressT,
            CandidateT,
            TransformErrorT,
            ProgressT,
            ResultT,
        ],
        phases: StagedIngestionPhases | None = None,
    ) -> None:
        self._strategy = strategy
        self._phases = phases or StagedIngestionPhases()

    def run(
        self,
        *,
        resolved_root: Path,
        run_id: int,
        progress: ProgressT,
        persistence: PersistenceScopeT,
    ) -> ResultT:
        """Run the staged ingestion flow and return the connector result."""

        try:
            progress.start_phase(phase=self._phases.discovery, total=None)
            discovered_units = list(
                self._strategy.discover_units(
                    root=resolved_root,
                    on_unit_discovered=lambda unit, count: progress.mark_discovered(
                        path=self._strategy.describe_unit(unit=unit),
                        discovered_file_count=count,
                    ),
                )
            )
            progress.finish_phase()

            progress.start_phase(
                phase=self._phases.fetch_transform,
                total=len(discovered_units),
            )
            fetched_payloads = self._strategy.fetch_payloads(
                units=discovered_units,
                on_batch_progress=progress.mark_metadata_batch,
            )
            candidates, transform_errors = self._build_candidates(
                resolved_root=resolved_root,
                discovered_units=discovered_units,
                fetched_payloads=fetched_payloads,
                progress=progress,
            )
            progress.finish_phase()

            missing_from_source_count = persistence.count_missing_from_source(
                resolved_root=resolved_root,
                discovered_units=discovered_units,
                candidates=candidates,
            )
            progress.mark_missing_from_source(
                missing_from_source_count=missing_from_source_count
            )

            progress.start_phase(
                phase=self._phases.persistence,
                total=len(candidates),
            )
            for candidate in candidates:
                progress.mark_persisted(outcome=persistence.persist(candidate=candidate))
            persistence.commit()
            progress.finish_phase()

            status = "partial_failure" if transform_errors else "completed"
            progress.finish_run(status=status)
            return self._strategy.build_result(
                run_id=run_id,
                progress=progress,
                transform_errors=transform_errors,
            )
        except Exception:
            persistence.rollback()
            progress.fail_run()
            raise
        finally:
            persistence.close()

    def _build_candidates(
        self,
        *,
        resolved_root: Path,
        discovered_units: Sequence[DiscoveredUnitT],
        fetched_payloads: FetchedPayloadT,
        progress: ProgressT,
    ) -> tuple[list[CandidateT], list[TransformErrorT]]:
        candidates: list[CandidateT] = []
        transform_errors: list[TransformErrorT] = []
        for unit in discovered_units:
            try:
                candidates.append(
                    self._strategy.build_candidate(
                        root=resolved_root,
                        unit=unit,
                        fetched_payloads=fetched_payloads,
                    )
                )
                progress.mark_analysis_success()
            except Exception as error:
                transform_error = self._strategy.build_transform_error(
                    unit=unit,
                    error=error,
                )
                transform_errors.append(transform_error)
                progress.mark_analysis_failure(error=transform_error)
        return candidates, transform_errors


__all__ = [
    "StagedIngestionPhases",
    "StagedIngestionProgress",
    "StagedIngestionRunner",
]
