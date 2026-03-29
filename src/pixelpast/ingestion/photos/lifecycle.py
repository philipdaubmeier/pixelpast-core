"""Operational lifecycle helpers for photo ingestion runs."""

from __future__ import annotations

from pathlib import Path

from pixelpast.persistence.repositories import (
    AssetRepository,
    SourceRepository,
)
from pixelpast.shared.job_run_coordinator import JobRunCoordinatorBase
from pixelpast.shared.runtime import RuntimeContext

PHOTO_SOURCE_NAME = "Photos"
PHOTO_JOB_NAME = "photos"
PHOTO_JOB_TYPE = "ingest"
PHOTO_MODE = "full"
PHOTO_INITIAL_PHASE = "initializing"


class PhotoIngestionRunCoordinator(JobRunCoordinatorBase):
    """Coordinate source state and run bootstrap for photo ingestion."""

    job_type = PHOTO_JOB_TYPE
    job_name = PHOTO_JOB_NAME
    mode = PHOTO_MODE
    initial_phase = PHOTO_INITIAL_PHASE

    def create_run(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
    ) -> int:
        """Create or update the photo source and persist a new run."""

        return self._create_run(runtime=runtime, resolved_root=resolved_root)

    def _bootstrap_source_state(
        self,
        *,
        session,
        runtime: RuntimeContext,
        resolved_root: Path | None = None,
        **kwargs: object,
    ) -> None:
        del runtime, kwargs
        if resolved_root is None:
            raise ValueError("Photo ingestion run bootstrap requires resolved_root.")
        SourceRepository(session).get_or_create(
            name=PHOTO_SOURCE_NAME,
            source_type=PHOTO_JOB_NAME,
            config={"root_path": resolved_root.as_posix()},
        )

    def count_missing_from_source(
        self,
        *,
        asset_repository: AssetRepository,
        source_id: int,
        resolved_root: Path,
        discovered_paths: list[Path],
    ) -> int:
        """Count persisted photo assets below the root missing from discovery."""

        discovered_external_ids = {
            path.expanduser().resolve().as_posix() for path in discovered_paths
        }
        persisted_external_ids = set(
            asset_repository.list_external_ids_under_prefix(
                source_id=source_id,
                external_id_prefix=resolved_root.as_posix(),
            )
        )
        return len(persisted_external_ids - discovered_external_ids)

    def get_source_id(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
    ) -> int:
        """Return the canonical source identifier used for photo asset persistence."""

        session = runtime.session_factory()
        try:
            source = SourceRepository(session).get_or_create(
                name=PHOTO_SOURCE_NAME,
                source_type=PHOTO_JOB_NAME,
                config={"root_path": resolved_root.as_posix()},
            )
            session.commit()
            return source.id
        finally:
            session.close()


__all__ = [
    "PHOTO_JOB_NAME",
    "PHOTO_JOB_TYPE",
    "PHOTO_INITIAL_PHASE",
    "PHOTO_SOURCE_NAME",
    "PHOTO_MODE",
    "PhotoIngestionRunCoordinator",
]
