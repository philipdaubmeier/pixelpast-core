"""Photo-specific adapters for the reusable staged ingestion runner."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pixelpast.ingestion.photos.connector import PhotoConnector
from pixelpast.ingestion.photos.contracts import (
    PhotoAssetCandidate,
    PhotoDiscoveryError,
    PhotoIngestionResult,
)
from pixelpast.ingestion.photos.lifecycle import PhotoImportRunCoordinator
from pixelpast.ingestion.photos.persist import PhotoAssetPersister
from pixelpast.ingestion.photos.progress import PhotoIngestionProgressTracker
from pixelpast.persistence.repositories import (
    AssetRepository,
    PersonRepository,
    TagRepository,
)
from pixelpast.shared.runtime import RuntimeContext


class PhotoIngestionPersistenceScope:
    """Wrap the photo persistence transaction boundary for the staged runner."""

    def __init__(
        self,
        *,
        runtime: RuntimeContext,
        lifecycle: PhotoImportRunCoordinator,
    ) -> None:
        session = runtime.session_factory()
        self._session = session
        self._lifecycle = lifecycle
        self._asset_repository = AssetRepository(session)
        self._persister = PhotoAssetPersister(
            asset_repository=self._asset_repository,
            tag_repository=TagRepository(session),
            person_repository=PersonRepository(session),
        )

    def count_missing_from_source(
        self,
        *,
        resolved_root: Path,
        discovered_units: Sequence[Path],
    ) -> int:
        """Count persisted photo assets missing from the current discovery set."""

        return self._lifecycle.count_missing_from_source(
            asset_repository=self._asset_repository,
            resolved_root=resolved_root,
            discovered_paths=list(discovered_units),
        )

    def persist(self, *, candidate: PhotoAssetCandidate) -> str:
        """Persist one canonical photo asset candidate."""

        return self._persister.persist(asset=candidate)

    def commit(self) -> None:
        """Commit the open photo ingestion transaction."""

        self._session.commit()

    def rollback(self) -> None:
        """Rollback the open photo ingestion transaction."""

        self._session.rollback()

    def close(self) -> None:
        """Close the open photo ingestion session."""

        self._session.close()


class PhotoStagedIngestionStrategy:
    """Bind the photo connector to the generic staged runner contract."""

    def __init__(self, *, connector: PhotoConnector) -> None:
        self._connector = connector

    def discover_units(
        self,
        *,
        root: Path,
        on_unit_discovered,
    ) -> Sequence[Path]:
        """Discover supported photo files below the configured root."""

        return self._connector.discover_paths(
            root,
            on_path_discovered=on_unit_discovered,
        )

    def fetch_payloads(
        self,
        *,
        units: Sequence[Path],
        on_batch_progress,
    ) -> dict[str, dict[str, Any]]:
        """Fetch grouped metadata for all discovered photo files."""

        return self._connector.extract_metadata_by_path(
            paths=list(units),
            on_batch_progress=on_batch_progress,
        )

    def build_candidate(
        self,
        *,
        root: Path,
        unit: Path,
        fetched_payloads: dict[str, dict[str, Any]],
    ) -> PhotoAssetCandidate:
        """Build one canonical photo asset candidate from fetched metadata."""

        return self._connector.build_asset_candidate(
            root=root,
            path=unit,
            metadata=fetched_payloads.get(unit.resolve().as_posix(), {}),
        )

    def build_transform_error(
        self,
        *,
        unit: Path,
        error: Exception,
    ) -> PhotoDiscoveryError:
        """Convert one transform failure into the public photo error contract."""

        return PhotoDiscoveryError(path=unit, message=str(error))

    def describe_unit(self, *, unit: Path) -> str:
        """Return a stable progress label for a discovered photo file."""

        return unit.as_posix()

    def build_result(
        self,
        *,
        import_run_id: int,
        progress: PhotoIngestionProgressTracker,
        transform_errors: Sequence[PhotoDiscoveryError],
    ) -> PhotoIngestionResult:
        """Render the public photo ingestion summary from staged runner state."""

        counters = progress.counters
        status = "partial_failure" if transform_errors else "completed"
        return PhotoIngestionResult(
            import_run_id=import_run_id,
            processed_asset_count=counters.items_persisted,
            error_count=counters.failed,
            status=status,
            discovered_file_count=counters.discovered_file_count,
            analyzed_file_count=counters.analyzed_file_count,
            analysis_failed_file_count=counters.analysis_failed_file_count,
            assets_persisted=counters.items_persisted,
            inserted_asset_count=counters.inserted,
            updated_asset_count=counters.updated,
            unchanged_asset_count=counters.unchanged,
            skipped_asset_count=counters.skipped,
            missing_from_source_count=counters.missing_from_source,
            metadata_batches_submitted=counters.metadata_batches_submitted,
            metadata_batches_completed=counters.metadata_batches_completed,
        )


__all__ = [
    "PhotoIngestionPersistenceScope",
    "PhotoStagedIngestionStrategy",
]
