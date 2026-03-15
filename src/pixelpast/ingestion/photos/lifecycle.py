"""Operational lifecycle helpers for photo ingestion runs."""

from __future__ import annotations

from pathlib import Path

from pixelpast.persistence.repositories import (
    AssetRepository,
    JobRunRepository,
    SourceRepository,
)
from pixelpast.shared.progress import build_initial_job_progress_payload
from pixelpast.shared.runtime import RuntimeContext

PHOTO_SOURCE_NAME = "Photos"
PHOTO_JOB_NAME = "photos"
PHOTO_JOB_TYPE = "ingest"
PHOTO_MODE = "full"
PHOTO_INITIAL_PHASE = "initializing"


class PhotoIngestionRunCoordinator:
    """Coordinate source state and run bootstrap for photo ingestion."""

    def create_run(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
    ) -> int:
        """Create or update the photo source and persist a new run."""

        session = runtime.session_factory()
        try:
            source_repository = SourceRepository(session)
            job_run_repository = JobRunRepository(session)
            source_repository.get_or_create(
                name=PHOTO_SOURCE_NAME,
                source_type=PHOTO_JOB_NAME,
                config={"root_path": resolved_root.as_posix()},
            )
            job_run = job_run_repository.create(
                job_type=PHOTO_JOB_TYPE,
                job=PHOTO_JOB_NAME,
                mode=PHOTO_MODE,
                phase=PHOTO_INITIAL_PHASE,
                progress_json=build_initial_job_progress_payload(),
            )
            session.commit()
            return job_run.id
        finally:
            session.close()

    def count_missing_from_source(
        self,
        *,
        asset_repository: AssetRepository,
        resolved_root: Path,
        discovered_paths: list[Path],
    ) -> int:
        """Count persisted photo assets below the root missing from discovery."""

        discovered_external_ids = {
            path.expanduser().resolve().as_posix() for path in discovered_paths
        }
        persisted_external_ids = set(
            asset_repository.list_external_ids_under_prefix(
                media_type="photo",
                external_id_prefix=resolved_root.as_posix(),
            )
        )
        return len(persisted_external_ids - discovered_external_ids)


__all__ = [
    "PHOTO_JOB_NAME",
    "PHOTO_JOB_TYPE",
    "PHOTO_INITIAL_PHASE",
    "PHOTO_SOURCE_NAME",
    "PHOTO_MODE",
    "PhotoIngestionRunCoordinator",
]
