"""Operational lifecycle helpers for photo ingestion runs."""

from __future__ import annotations

from pathlib import Path

from pixelpast.persistence.repositories import (
    AssetRepository,
    ImportRunRepository,
    SourceRepository,
)
from pixelpast.shared.runtime import RuntimeContext

PHOTO_SOURCE_NAME = "Photos"
PHOTO_SOURCE_TYPE = "photos"
PHOTO_IMPORT_MODE = "full"
PHOTO_INITIAL_PHASE = "initializing"


def build_initial_photo_import_progress_payload() -> dict[str, int | None]:
    """Return the authoritative zeroed progress payload for a new photo run."""

    return {
        "total": None,
        "completed": 0,
        "inserted": 0,
        "updated": 0,
        "unchanged": 0,
        "skipped": 0,
        "failed": 0,
        "missing_from_source": 0,
    }


class PhotoImportRunCoordinator:
    """Coordinate source state and import-run bootstrap for photo ingestion."""

    def create_import_run(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
    ) -> int:
        """Create or update the photo source and persist a new import run."""

        session = runtime.session_factory()
        try:
            source_repository = SourceRepository(session)
            import_run_repository = ImportRunRepository(session)
            source = source_repository.get_or_create(
                name=PHOTO_SOURCE_NAME,
                source_type=PHOTO_SOURCE_TYPE,
                config={"root_path": resolved_root.as_posix()},
            )
            import_run = import_run_repository.create(
                source_id=source.id,
                mode=PHOTO_IMPORT_MODE,
                phase=PHOTO_INITIAL_PHASE,
                progress_json=build_initial_photo_import_progress_payload(),
            )
            session.commit()
            return import_run.id
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
    "PHOTO_IMPORT_MODE",
    "PHOTO_INITIAL_PHASE",
    "PHOTO_SOURCE_NAME",
    "PHOTO_SOURCE_TYPE",
    "PhotoImportRunCoordinator",
    "build_initial_photo_import_progress_payload",
]
