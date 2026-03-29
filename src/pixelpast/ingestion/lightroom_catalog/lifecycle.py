"""Operational lifecycle helpers for Lightroom catalog ingestion runs."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from pixelpast.ingestion.lightroom_catalog.contracts import (
    LightroomCatalogCandidate,
    LightroomCatalogDescriptor,
)
from pixelpast.persistence.repositories import JobRunRepository, SourceRepository
from pixelpast.shared.progress import build_initial_job_progress_payload
from pixelpast.shared.runtime import RuntimeContext

LIGHTROOM_CATALOG_JOB_NAME = "lightroom_catalog"
LIGHTROOM_CATALOG_JOB_TYPE = "ingest"
LIGHTROOM_CATALOG_MODE = "full"
LIGHTROOM_CATALOG_INITIAL_PHASE = "initializing"
LIGHTROOM_CATALOG_SOURCE_TYPE = "lightroom_catalog"


class LightroomCatalogIngestionRunCoordinator:
    """Coordinate source state and run bootstrap for Lightroom catalog ingest."""

    def create_run(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
    ) -> int:
        """Create or update the catalog-scoped source and persist a new run."""

        normalized_root = resolved_root.expanduser().resolve()
        session = runtime.session_factory()
        try:
            SourceRepository(session).upsert_by_external_id(
                external_id=build_lightroom_catalog_source_external_id(
                    catalog_path=normalized_root
                ),
                name=build_lightroom_catalog_source_name(catalog_path=normalized_root),
                source_type=LIGHTROOM_CATALOG_SOURCE_TYPE,
                config={"catalog_path": normalized_root.as_posix()},
            )
            job_run = JobRunRepository(session).create(
                job_type=LIGHTROOM_CATALOG_JOB_TYPE,
                job=LIGHTROOM_CATALOG_JOB_NAME,
                mode=LIGHTROOM_CATALOG_MODE,
                phase=LIGHTROOM_CATALOG_INITIAL_PHASE,
                progress_json={
                    **build_initial_job_progress_payload(),
                    "root_path": normalized_root.as_posix(),
                },
            )
            session.commit()
            return job_run.id
        finally:
            session.close()

    def count_missing_from_source(
        self,
        *,
        resolved_root: Path,
        discovered_catalogs: Sequence[LightroomCatalogDescriptor],
        candidates: Sequence[LightroomCatalogCandidate],
    ) -> int:
        """Return the explicit v1 missing-from-source count for Lightroom assets."""

        del resolved_root, discovered_catalogs, candidates
        return 0

    def get_source_id(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
    ) -> int:
        """Return the canonical source identifier used for Lightroom assets."""

        normalized_root = resolved_root.expanduser().resolve()
        session = runtime.session_factory()
        try:
            source = SourceRepository(session).upsert_by_external_id(
                external_id=build_lightroom_catalog_source_external_id(
                    catalog_path=normalized_root
                ),
                name=build_lightroom_catalog_source_name(catalog_path=normalized_root),
                source_type=LIGHTROOM_CATALOG_SOURCE_TYPE,
                config={"catalog_path": normalized_root.as_posix()},
            ).source
            session.commit()
            return source.id
        finally:
            session.close()


def build_lightroom_catalog_source_external_id(*, catalog_path: Path) -> str:
    """Return the stable source external identifier for one catalog path."""

    normalized_path = catalog_path.expanduser().resolve()
    return f"{LIGHTROOM_CATALOG_SOURCE_TYPE}:{normalized_path.as_posix()}"


def build_lightroom_catalog_source_name(*, catalog_path: Path) -> str:
    """Return a stable human-readable source name for one catalog path."""

    normalized_path = catalog_path.expanduser().resolve()
    return f"Lightroom Catalog: {normalized_path.as_posix()}"


__all__ = [
    "LIGHTROOM_CATALOG_INITIAL_PHASE",
    "LIGHTROOM_CATALOG_JOB_NAME",
    "LIGHTROOM_CATALOG_JOB_TYPE",
    "LIGHTROOM_CATALOG_MODE",
    "LIGHTROOM_CATALOG_SOURCE_TYPE",
    "LightroomCatalogIngestionRunCoordinator",
    "build_lightroom_catalog_source_external_id",
    "build_lightroom_catalog_source_name",
]
