"""Service orchestration for photo asset ingestion."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from time import monotonic

from pixelpast.ingestion.photos.connector import PhotoConnector
from pixelpast.ingestion.photos.contracts import (
    PhotoAssetCandidate,
    PhotoDiscoveryError,
    PhotoIngestionResult,
)
from pixelpast.ingestion.photos.lifecycle import PhotoImportRunCoordinator
from pixelpast.ingestion.photos.persist import PhotoAssetPersister
from pixelpast.ingestion.photos.progress import (
    PhotoIngestionProgressSnapshot,
    PhotoIngestionProgressTracker,
)
from pixelpast.ingestion.progress import IngestionProgressCallback
from pixelpast.persistence.repositories import (
    AssetRepository,
    PersonRepository,
    TagRepository,
)
from pixelpast.shared.runtime import RuntimeContext

_HEARTBEAT_INTERVAL_SECONDS = 10.0


class PhotoIngestionService:
    """Coordinate photo discovery with canonical persistence."""

    def __init__(
        self,
        connector: PhotoConnector | None = None,
        lifecycle: PhotoImportRunCoordinator | None = None,
        *,
        heartbeat_interval_seconds: float = _HEARTBEAT_INTERVAL_SECONDS,
        now_factory: Callable[[], datetime] | None = None,
        monotonic_factory: Callable[[], float] | None = None,
    ) -> None:
        self._connector = connector or PhotoConnector()
        self._lifecycle = lifecycle or PhotoImportRunCoordinator()
        self._heartbeat_interval_seconds = heartbeat_interval_seconds
        self._now_factory = now_factory
        self._monotonic_factory = monotonic_factory or monotonic

    def ingest(
        self,
        *,
        runtime: RuntimeContext,
        progress_callback: IngestionProgressCallback | None = None,
    ) -> PhotoIngestionResult:
        """Run the photo connector and persist canonical assets and import state."""

        photos_root = runtime.settings.photos_root
        if photos_root is None:
            raise ValueError(
                "Photo ingestion requires PIXELPAST_PHOTOS_ROOT to be configured."
            )

        resolved_root = photos_root.expanduser().resolve()
        import_run_id = self._lifecycle.create_import_run(
            runtime=runtime,
            resolved_root=resolved_root,
        )
        progress = PhotoIngestionProgressTracker(
            import_run_id=import_run_id,
            runtime=runtime,
            callback=progress_callback,
            heartbeat_interval_seconds=self._heartbeat_interval_seconds,
            now_factory=self._now_factory,
            monotonic_factory=self._monotonic_factory,
        )

        session = runtime.session_factory()
        asset_repository = AssetRepository(session)
        persister = PhotoAssetPersister(
            asset_repository=asset_repository,
            tag_repository=TagRepository(session),
            person_repository=PersonRepository(session),
        )

        try:
            progress.start_phase(phase="filesystem discovery", total=None)
            supported_paths = self._connector.discover_paths(
                resolved_root,
                on_path_discovered=lambda path, count: progress.mark_discovered(
                    path=path.as_posix(),
                    discovered_file_count=count,
                ),
            )
            progress.finish_phase()

            missing_from_source_count = self._lifecycle.count_missing_from_source(
                asset_repository=asset_repository,
                resolved_root=resolved_root,
                discovered_paths=supported_paths,
            )
            progress.mark_missing_from_source(
                missing_from_source_count=missing_from_source_count
            )

            progress.start_phase(
                phase="metadata extraction",
                total=len(supported_paths),
            )
            metadata_by_path = self._connector.extract_metadata_by_path(
                paths=supported_paths,
                on_batch_progress=progress.mark_metadata_batch,
            )
            assets, errors = self._analyze_assets(
                root=resolved_root,
                paths=supported_paths,
                metadata_by_path=metadata_by_path,
                progress=progress,
            )
            progress.finish_phase()

            progress.start_phase(
                phase="canonical persistence",
                total=len(assets),
            )
            for asset in assets:
                outcome = persister.persist(asset=asset)
                progress.mark_persisted(outcome=outcome)
            session.commit()
            progress.finish_phase()

            status = "partial_failure" if errors else "completed"
            progress.finish_run(status=status)
            return PhotoIngestionResult(
                import_run_id=import_run_id,
                processed_asset_count=progress.counters.items_persisted,
                error_count=progress.counters.analysis_failed_file_count,
                status=status,
                discovered_file_count=progress.counters.discovered_file_count,
                analyzed_file_count=progress.counters.analyzed_file_count,
                analysis_failed_file_count=progress.counters.analysis_failed_file_count,
                assets_persisted=progress.counters.items_persisted,
                inserted_asset_count=progress.counters.inserted_item_count,
                updated_asset_count=progress.counters.updated_item_count,
                unchanged_asset_count=progress.counters.unchanged_item_count,
                skipped_asset_count=progress.counters.skipped_item_count,
                missing_from_source_count=progress.counters.missing_from_source_count,
                metadata_batches_submitted=progress.counters.metadata_batches_submitted,
                metadata_batches_completed=progress.counters.metadata_batches_completed,
            )
        except Exception:
            session.rollback()
            progress.fail_run()
            raise
        finally:
            session.close()

    def _analyze_assets(
        self,
        *,
        root,
        paths,
        metadata_by_path,
        progress: PhotoIngestionProgressTracker,
    ) -> tuple[list[PhotoAssetCandidate], list[PhotoDiscoveryError]]:
        assets: list[PhotoAssetCandidate] = []
        errors: list[PhotoDiscoveryError] = []
        for path in paths:
            try:
                assets.append(
                    self._connector.build_asset_candidate(
                        root=root,
                        path=path,
                        metadata=metadata_by_path.get(path.resolve().as_posix(), {}),
                    )
                )
                progress.mark_analysis_success()
            except Exception as error:
                issue = PhotoDiscoveryError(path=path, message=str(error))
                errors.append(issue)
                progress.mark_analysis_failure(error=issue)
        return assets, errors


__all__ = [
    "PhotoIngestionProgressSnapshot",
    "PhotoIngestionResult",
    "PhotoIngestionService",
]
