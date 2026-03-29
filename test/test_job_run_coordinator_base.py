from __future__ import annotations

import shutil
from pathlib import Path

from pixelpast.persistence.models import JobRun
from pixelpast.persistence.base import Base
from pixelpast.persistence.session import (
    create_database_engine,
    create_session_factory,
)
from pixelpast.shared.job_run_coordinator import JobRunCoordinatorBase
from pixelpast.shared.runtime import RuntimeContext
from pixelpast.shared.settings import Settings


class StubCoordinator(JobRunCoordinatorBase):
    job_type = "ingest"
    job_name = "stub"
    mode = "full"
    initial_phase = "initializing"

    def __init__(self) -> None:
        self.bootstrap_calls: list[str] = []

    def create_run(self, *, runtime: RuntimeContext, resolved_root: Path) -> int:
        return self._create_run(runtime=runtime, resolved_root=resolved_root)

    def _bootstrap_source_state(self, **kwargs) -> None:
        self.bootstrap_calls.append("bootstrap")

    def _include_root_path_in_payload(self) -> bool:
        return True


def test_job_run_coordinator_base_bootstraps_before_persisting_job_run() -> None:
    test_root = Path("var/test_job_run_coordinator_base")
    if test_root.exists():
        shutil.rmtree(test_root)
    test_root.mkdir(parents=True, exist_ok=True)

    database_path = test_root / "pixelpast.sqlite"
    settings = Settings(database_url=f"sqlite:///{database_path.as_posix()}")
    engine = create_database_engine(settings)
    session_factory = create_session_factory(settings=settings, engine=engine)
    Base.metadata.create_all(bind=engine)
    runtime = RuntimeContext(
        settings=settings,
        engine=engine,
        session_factory=session_factory,
    )
    coordinator = StubCoordinator()
    root = test_root / "imports"
    root.mkdir()

    run_id = coordinator.create_run(runtime=runtime, resolved_root=root.resolve())

    with runtime.session_factory() as session:
        job_run = session.get(JobRun, run_id)
        assert job_run is not None
        assert job_run.job == "stub"
        assert job_run.type == "ingest"
        assert job_run.mode == "full"
        assert job_run.phase == "initializing"
        assert job_run.progress_json == {
            "total": None,
            "completed": 0,
            "inserted": 0,
            "updated": 0,
            "unchanged": 0,
            "skipped": 0,
            "failed": 0,
            "missing_from_source": 0,
            "root_path": root.resolve().as_posix(),
        }

    assert coordinator.bootstrap_calls == ["bootstrap"]
