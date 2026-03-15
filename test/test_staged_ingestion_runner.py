"""Tests for the reusable staged ingestion runner."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from pixelpast.ingestion.staged import StagedIngestionRunner


def test_staged_runner_handles_partial_transform_failures_and_completes() -> None:
    progress = _FakeProgress()
    persistence = _FakePersistenceScope()
    runner = StagedIngestionRunner(strategy=_FakeStrategy())

    result = runner.run(
        resolved_root=Path("/timeline/photos"),
        run_id=41,
        progress=progress,
        persistence=persistence,
    )

    assert result == {
        "run_id": 41,
        "status": "partial_failure",
        "processed": 2,
        "errors": ["bad.jpg: broken metadata"],
    }
    assert progress.started_phases == [
        ("filesystem discovery", None),
        ("metadata extraction", 3),
        ("canonical persistence", 2),
    ]
    assert progress.finished_phases == [
        "filesystem discovery",
        "metadata extraction",
        "canonical persistence",
    ]
    assert progress.discovered == [
        ("/timeline/photos/first.jpg", 1),
        ("/timeline/photos/bad.jpg", 2),
        ("/timeline/photos/second.jpg", 3),
    ]
    assert progress.metadata_batches == ["submitted:3", "completed:3"]
    assert progress.analysis_failures == ["bad.jpg: broken metadata"]
    assert progress.persisted_outcomes == ["inserted", "updated"]
    assert progress.finished_status == "partial_failure"
    assert progress.failed is False
    assert persistence.count_calls == 1
    assert persistence.persisted_candidates == ["first", "second"]
    assert persistence.committed is True
    assert persistence.rolled_back is False
    assert persistence.closed is True


def test_staged_runner_rolls_back_and_marks_failure_on_persist_error() -> None:
    progress = _FakeProgress()
    persistence = _FakePersistenceScope(fail_on_candidate="second")
    runner = StagedIngestionRunner(strategy=_FakeStrategy())

    with pytest.raises(RuntimeError, match="persist boom"):
        runner.run(
            resolved_root=Path("/timeline/photos"),
            run_id=99,
            progress=progress,
            persistence=persistence,
        )

    assert progress.finished_status is None
    assert progress.failed is True
    assert persistence.committed is False
    assert persistence.rolled_back is True
    assert persistence.closed is True


@dataclass
class _FakeCounters:
    items_persisted: int = 0
    analysis_failed_file_count: int = 0


class _FakeProgress:
    def __init__(self) -> None:
        self.counters = _FakeCounters()
        self.current_phase = "initializing"
        self.started_phases: list[tuple[str, int | None]] = []
        self.finished_phases: list[str] = []
        self.discovered: list[tuple[str, int]] = []
        self.metadata_batches: list[str] = []
        self.analysis_failures: list[str] = []
        self.persisted_outcomes: list[str] = []
        self.finished_status: str | None = None
        self.failed = False

    def start_phase(self, *, phase: str, total: int | None) -> None:
        self.current_phase = phase
        self.started_phases.append((phase, total))

    def finish_phase(self) -> None:
        self.finished_phases.append(self.current_phase)

    def mark_discovered(self, *, path: str, discovered_file_count: int) -> None:
        self.discovered.append((path, discovered_file_count))

    def mark_missing_from_source(self, *, missing_from_source_count: int) -> None:
        self.missing_from_source_count = missing_from_source_count

    def mark_metadata_batch(self, progress: str) -> None:
        self.metadata_batches.append(progress)

    def mark_analysis_success(self) -> None:
        return None

    def mark_analysis_failure(self, *, error: str) -> None:
        self.counters.analysis_failed_file_count += 1
        self.analysis_failures.append(error)

    def mark_persisted(self, *, outcome: str) -> None:
        self.counters.items_persisted += 1
        self.persisted_outcomes.append(outcome)

    def finish_run(self, *, status: str) -> None:
        self.finished_status = status

    def fail_run(self) -> None:
        self.failed = True


class _FakePersistenceScope:
    def __init__(self, *, fail_on_candidate: str | None = None) -> None:
        self._fail_on_candidate = fail_on_candidate
        self.count_calls = 0
        self.persisted_candidates: list[str] = []
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def count_missing_from_source(
        self,
        *,
        resolved_root: Path,
        discovered_units,
        candidates,
    ) -> int:
        del resolved_root, discovered_units, candidates
        self.count_calls += 1
        return 0

    def persist(self, *, candidate: str) -> str:
        self.persisted_candidates.append(candidate)
        if candidate == self._fail_on_candidate:
            raise RuntimeError("persist boom")
        return "inserted" if candidate == "first" else "updated"

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


class _FakeStrategy:
    def discover_units(self, *, root: Path, on_unit_discovered):
        units = [root / "first.jpg", root / "bad.jpg", root / "second.jpg"]
        for index, unit in enumerate(units, start=1):
            on_unit_discovered(unit, index)
        return units

    def fetch_payloads(self, *, units, on_batch_progress):
        on_batch_progress(f"submitted:{len(units)}")
        on_batch_progress(f"completed:{len(units)}")
        return {unit.name: unit.stem for unit in units}

    def build_candidate(self, *, root: Path, unit: Path, fetched_payloads):
        del root
        if unit.name == "bad.jpg":
            raise RuntimeError("broken metadata")
        return fetched_payloads[unit.name]

    def build_transform_error(self, *, unit: Path, error: Exception) -> str:
        return f"{unit.name}: {error}"

    def describe_unit(self, *, unit: Path) -> str:
        return unit.as_posix()

    def build_result(
        self,
        *,
        run_id: int,
        progress: _FakeProgress,
        transform_errors,
    ):
        return {
            "run_id": run_id,
            "status": "partial_failure" if transform_errors else "completed",
            "processed": progress.counters.items_persisted,
            "errors": list(transform_errors),
        }
