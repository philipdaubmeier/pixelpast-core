"""Service orchestration for photo asset ingestion."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic

from pixelpast.ingestion.progress import (
    IngestionProgressCallback,
    IngestionProgressSnapshot,
)
from pixelpast.ingestion.photos.connector import PhotoConnector
from pixelpast.ingestion.photos.contracts import (
    PhotoAssetCandidate,
    PhotoDiscoveryError,
    PhotoIngestionProgressSnapshot,
    PhotoIngestionResult,
    PhotoMetadataBatchProgress,
)
from pixelpast.ingestion.photos.persist import PhotoAssetPersister
from pixelpast.persistence.repositories import (
    AssetRepository,
    ImportRunRepository,
    PersonRepository,
    SourceRepository,
    TagRepository,
)
from pixelpast.shared.runtime import RuntimeContext

logger = logging.getLogger(__name__)

_HEARTBEAT_INTERVAL_SECONDS = 10.0


@dataclass(slots=True)
class _PhotoIngestionCounters:
    discovered_file_count: int = 0
    analyzed_file_count: int = 0
    analysis_failed_file_count: int = 0
    metadata_batches_submitted: int = 0
    metadata_batches_completed: int = 0
    items_persisted: int = 0
    inserted_item_count: int = 0
    updated_item_count: int = 0
    unchanged_item_count: int = 0
    skipped_item_count: int = 0
    missing_from_source_count: int = 0


class _PhotoIngestionProgressTracker:
    """Persist and emit runtime progress snapshots for one photo ingest run."""

    def __init__(
        self,
        *,
        import_run_id: int,
        runtime: RuntimeContext,
        callback: IngestionProgressCallback | None = None,
        heartbeat_interval_seconds: float = _HEARTBEAT_INTERVAL_SECONDS,
        now_factory: Callable[[], datetime] | None = None,
        monotonic_factory: Callable[[], float] | None = None,
    ) -> None:
        self._import_run_id = import_run_id
        self._runtime = runtime
        self._callback = callback
        self._heartbeat_interval_seconds = heartbeat_interval_seconds
        self._now_factory = now_factory or _utc_now
        self._monotonic_factory = monotonic_factory or monotonic
        self._counters = _PhotoIngestionCounters()
        self._phase = "initializing"
        self._phase_total: int | None = None
        self._phase_completed = 0
        self._current_batch_index: int | None = None
        self._current_batch_total: int | None = None
        self._current_batch_size: int | None = None
        self._status = "running"
        self._last_heartbeat_at: datetime | None = None
        self._last_persist_monotonic: float | None = None

    def start_phase(self, *, phase: str, total: int | None) -> None:
        """Enter a new operational phase and persist the transition immediately."""

        self._phase = phase
        self._phase_total = total
        self._phase_completed = 0
        self._current_batch_index = None
        self._current_batch_total = None
        self._current_batch_size = None
        logger.info(
            "photo ingest phase started",
            extra={
                "import_run_id": self._import_run_id,
                "phase": phase,
                "phase_total": total,
            },
        )
        self._emit(event="phase_started", phase_status="started", force_persist=True)

    def mark_discovered(self, *, path: str, discovered_file_count: int) -> None:
        """Update discovery counts as supported files are found."""

        self._counters.discovered_file_count = discovered_file_count
        self._phase_total = discovered_file_count
        self._phase_completed = discovered_file_count
        logger.info(
            "photo ingest discovery progress",
            extra={
                "import_run_id": self._import_run_id,
                "phase": self._phase,
                "path": path,
                "discovered_file_count": discovered_file_count,
            },
        )
        self._emit(event="progress", phase_status="running")

    def finish_phase(self) -> None:
        """Persist the end of the current phase."""

        if self._phase_total is None:
            self._phase_total = self._phase_completed
        logger.info(
            "photo ingest phase completed",
            extra={
                "import_run_id": self._import_run_id,
                "phase": self._phase,
                "phase_total": self._phase_total,
                "phase_completed": self._phase_completed,
            },
        )
        self._emit(event="phase_completed", phase_status="completed", force_persist=True)

    def mark_missing_from_source(self, *, missing_from_source_count: int) -> None:
        """Record the informational count of known assets missing from the source."""

        self._counters.missing_from_source_count = missing_from_source_count
        logger.info(
            "photo ingest missing-from-source count",
            extra={
                "import_run_id": self._import_run_id,
                "missing_from_source_count": missing_from_source_count,
            },
        )
        self._emit(event="progress", phase_status="running", force_persist=True)

    def mark_metadata_batch(self, progress: PhotoMetadataBatchProgress) -> None:
        """Record metadata batch submission and completion progress."""

        self._current_batch_index = progress.batch_index
        self._current_batch_total = progress.batch_total
        self._current_batch_size = progress.batch_size
        if progress.event == "submitted":
            self._counters.metadata_batches_submitted += 1
        elif progress.event == "completed":
            self._counters.metadata_batches_completed += 1

        logger.info(
            "photo ingest metadata batch progress",
            extra={
                "import_run_id": self._import_run_id,
                "phase": self._phase,
                "batch_event": progress.event,
                "batch_index": progress.batch_index,
                "batch_total": progress.batch_total,
                "batch_size": progress.batch_size,
                "metadata_batches_submitted": self._counters.metadata_batches_submitted,
                "metadata_batches_completed": self._counters.metadata_batches_completed,
            },
        )
        self._emit(event=f"metadata_batch_{progress.event}", phase_status="running")

    def mark_analysis_success(self) -> None:
        """Record one successfully analyzed file."""

        self._counters.analyzed_file_count += 1
        self._phase_completed = (
            self._counters.analyzed_file_count
            + self._counters.analysis_failed_file_count
        )
        self._emit(event="progress", phase_status="running")

    def mark_analysis_failure(self, *, error: PhotoDiscoveryError) -> None:
        """Record one file that failed during analysis."""

        self._counters.analysis_failed_file_count += 1
        self._phase_completed = (
            self._counters.analyzed_file_count
            + self._counters.analysis_failed_file_count
        )
        logger.warning(
            "photo ingestion skipped file",
            extra={
                "import_run_id": self._import_run_id,
                "phase": self._phase,
                "path": error.path.as_posix(),
                "reason": error.message,
            },
        )
        self._emit(event="progress", phase_status="running", force_persist=True)

    def mark_persisted(self, *, outcome: str) -> None:
        """Record one completed persistence outcome for an analyzed asset."""

        self._phase_completed += 1
        if outcome == "inserted":
            self._counters.inserted_item_count += 1
            self._counters.items_persisted += 1
        elif outcome == "updated":
            self._counters.updated_item_count += 1
            self._counters.items_persisted += 1
        elif outcome == "unchanged":
            self._counters.unchanged_item_count += 1
            self._counters.items_persisted += 1
        elif outcome == "skipped":
            self._counters.skipped_item_count += 1
        else:
            raise ValueError(f"Unsupported persistence outcome: {outcome}")

        logger.info(
            "photo ingest persistence progress",
            extra={
                "import_run_id": self._import_run_id,
                "phase": self._phase,
                "phase_total": self._phase_total,
                "phase_completed": self._phase_completed,
                "items_persisted": self._counters.items_persisted,
                "inserted_item_count": self._counters.inserted_item_count,
                "updated_item_count": self._counters.updated_item_count,
                "unchanged_item_count": self._counters.unchanged_item_count,
                "skipped_item_count": self._counters.skipped_item_count,
            },
        )
        self._emit(event="progress", phase_status="running")

    def finish_run(self, *, status: str) -> IngestionProgressSnapshot:
        """Persist the terminal success or partial-failure state."""

        self._status = status
        self._phase = "finalization"
        self._phase_total = 1
        self._phase_completed = 1
        logger.info(
            "photo ingest finalization started",
            extra={
                "import_run_id": self._import_run_id,
                "status": status,
            },
        )
        self._emit(event="phase_started", phase_status="started", force_persist=True)
        self._persist_terminal_state(status=status)
        snapshot = self._build_snapshot(
            event="run_finished",
            phase_status="completed",
            heartbeat_written=True,
        )
        logger.info(
            "photo ingest completed",
            extra={
                "import_run_id": self._import_run_id,
                "status": status,
                **self._progress_payload(),
            },
        )
        if self._callback is not None:
            self._callback(snapshot)
        return snapshot

    def fail_run(self) -> IngestionProgressSnapshot:
        """Persist the terminal failed state using the current counters."""

        self._status = "failed"
        self._persist_terminal_state(status="failed")
        snapshot = self._build_snapshot(
            event="run_failed",
            phase_status="failed",
            heartbeat_written=True,
        )
        logger.error(
            "photo ingest failed",
            extra={
                "import_run_id": self._import_run_id,
                "phase": self._phase,
                **self._progress_payload(),
            },
        )
        if self._callback is not None:
            self._callback(snapshot)
        return snapshot

    @property
    def counters(self) -> _PhotoIngestionCounters:
        """Expose the current counters for final result construction."""

        return self._counters

    def _emit(
        self,
        *,
        event: str,
        phase_status: str,
        force_persist: bool = False,
    ) -> IngestionProgressSnapshot:
        heartbeat_written = self._persist_progress(force=force_persist)
        snapshot = self._build_snapshot(
            event=event,
            phase_status=phase_status,
            heartbeat_written=heartbeat_written,
        )
        if self._callback is not None:
            self._callback(snapshot)
        return snapshot

    def _persist_progress(self, *, force: bool) -> bool:
        if not force and not self._heartbeat_due():
            return False

        heartbeat_at = self._now_factory()
        with self._runtime.session_factory() as session:
            repository = ImportRunRepository(session)
            import_run = repository.update_progress(
                import_run_id=self._import_run_id,
                phase=self._phase,
                progress_json=self._progress_payload(),
                last_heartbeat_at=heartbeat_at,
                status=self._status,
            )
            if import_run is None:
                raise RuntimeError(
                    f"ImportRun {self._import_run_id} is missing from persistence."
                )
            session.commit()

        self._last_heartbeat_at = heartbeat_at
        self._last_persist_monotonic = self._monotonic_factory()
        logger.info(
            "photo ingest heartbeat written",
            extra={
                "import_run_id": self._import_run_id,
                "phase": self._phase,
                "last_heartbeat_at": heartbeat_at.isoformat(),
                "status": self._status,
            },
        )
        return True

    def _persist_terminal_state(self, *, status: str) -> datetime:
        heartbeat_at = self._now_factory()
        with self._runtime.session_factory() as session:
            repository = ImportRunRepository(session)
            import_run = repository.mark_finished_by_id(
                import_run_id=self._import_run_id,
                status=status,
                phase=self._phase,
                last_heartbeat_at=heartbeat_at,
                progress_json=self._progress_payload(),
            )
            if import_run is None:
                raise RuntimeError(
                    f"ImportRun {self._import_run_id} is missing from persistence."
                )
            session.commit()

        self._last_heartbeat_at = heartbeat_at
        self._last_persist_monotonic = self._monotonic_factory()
        return heartbeat_at

    def _heartbeat_due(self) -> bool:
        if self._last_persist_monotonic is None:
            return True
        return (
            self._monotonic_factory() - self._last_persist_monotonic
            >= self._heartbeat_interval_seconds
        )

    def _progress_payload(self) -> dict[str, int | None]:
        return {
            "phase_total": self._phase_total,
            "phase_completed": self._phase_completed,
            "discovered_file_count": self._counters.discovered_file_count,
            "analyzed_file_count": self._counters.analyzed_file_count,
            "analysis_failed_file_count": self._counters.analysis_failed_file_count,
            "metadata_batches_submitted": self._counters.metadata_batches_submitted,
            "metadata_batches_completed": self._counters.metadata_batches_completed,
            "items_persisted": self._counters.items_persisted,
            "inserted_item_count": self._counters.inserted_item_count,
            "updated_item_count": self._counters.updated_item_count,
            "unchanged_item_count": self._counters.unchanged_item_count,
            "skipped_item_count": self._counters.skipped_item_count,
            "missing_from_source_count": self._counters.missing_from_source_count,
            "current_batch_index": self._current_batch_index,
            "current_batch_total": self._current_batch_total,
            "current_batch_size": self._current_batch_size,
        }

    def _build_snapshot(
        self,
        *,
        event: str,
        phase_status: str,
        heartbeat_written: bool,
    ) -> IngestionProgressSnapshot:
        return IngestionProgressSnapshot(
            event=event,
            source="photos",
            import_run_id=self._import_run_id,
            phase=self._phase,
            phase_status=phase_status,
            phase_total=self._phase_total,
            phase_completed=self._phase_completed,
            status=self._status,
            discovered_file_count=self._counters.discovered_file_count,
            analyzed_file_count=self._counters.analyzed_file_count,
            analysis_failed_file_count=self._counters.analysis_failed_file_count,
            metadata_batches_submitted=self._counters.metadata_batches_submitted,
            metadata_batches_completed=self._counters.metadata_batches_completed,
            items_persisted=self._counters.items_persisted,
            inserted_item_count=self._counters.inserted_item_count,
            updated_item_count=self._counters.updated_item_count,
            unchanged_item_count=self._counters.unchanged_item_count,
            skipped_item_count=self._counters.skipped_item_count,
            missing_from_source_count=self._counters.missing_from_source_count,
            current_batch_index=self._current_batch_index,
            current_batch_total=self._current_batch_total,
            current_batch_size=self._current_batch_size,
            heartbeat_written=heartbeat_written,
        )


class PhotoIngestionService:
    """Coordinate photo discovery with canonical persistence."""

    def __init__(
        self,
        connector: PhotoConnector | None = None,
        *,
        heartbeat_interval_seconds: float = _HEARTBEAT_INTERVAL_SECONDS,
        now_factory: Callable[[], datetime] | None = None,
        monotonic_factory: Callable[[], float] | None = None,
    ) -> None:
        self._connector = connector or PhotoConnector()
        self._heartbeat_interval_seconds = heartbeat_interval_seconds
        self._now_factory = now_factory or _utc_now
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
        import_run_id = self._create_import_run(
            runtime=runtime,
            resolved_root=resolved_root,
        )
        progress = _PhotoIngestionProgressTracker(
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

            discovered_external_ids = {
                path.expanduser().resolve().as_posix() for path in supported_paths
            }
            missing_from_source_count = len(
                set(
                    asset_repository.list_external_ids_under_prefix(
                        media_type="photo",
                        external_id_prefix=resolved_root.as_posix(),
                    )
                )
                - discovered_external_ids
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

    def _create_import_run(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root,
    ) -> int:
        session = runtime.session_factory()
        source_repository = SourceRepository(session)
        import_run_repository = ImportRunRepository(session)
        try:
            source = source_repository.get_or_create(
                name="Photos",
                source_type="photos",
                config={"root_path": resolved_root.as_posix()},
            )
            import_run = import_run_repository.create(
                source_id=source.id,
                mode="full",
                phase="initializing",
                progress_json={
                    "phase_total": None,
                    "phase_completed": 0,
                    "discovered_file_count": 0,
                    "analyzed_file_count": 0,
                    "analysis_failed_file_count": 0,
                    "metadata_batches_submitted": 0,
                    "metadata_batches_completed": 0,
                    "items_persisted": 0,
                    "inserted_item_count": 0,
                    "updated_item_count": 0,
                    "unchanged_item_count": 0,
                    "skipped_item_count": 0,
                    "missing_from_source_count": 0,
                    "current_batch_index": None,
                    "current_batch_total": None,
                    "current_batch_size": None,
                },
            )
            session.commit()
            return import_run.id
        finally:
            session.close()

    def _analyze_assets(
        self,
        *,
        root,
        paths,
        metadata_by_path,
        progress: _PhotoIngestionProgressTracker,
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


def _utc_now() -> datetime:
    """Return the current aware UTC time."""

    return datetime.now(UTC)
