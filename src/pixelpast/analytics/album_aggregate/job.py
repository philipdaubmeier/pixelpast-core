"""Album aggregate derive job composition root."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from pixelpast.analytics.album_aggregate.builder import (
    AlbumAggregateBuildResult,
    build_album_aggregate_snapshots,
)
from pixelpast.analytics.album_aggregate.loading import (
    AlbumAggregateCanonicalInputs,
    AlbumAggregateCanonicalLoader,
)
from pixelpast.analytics.album_aggregate.persistence import (
    AlbumAggregatePersistenceResult,
    AlbumAggregateSnapshotPersister,
)
from pixelpast.analytics.album_aggregate.progress import (
    ALBUM_AGGREGATE_JOB_NAME,
    AlbumAggregateProgressTracker,
)
from pixelpast.analytics.lifecycle import DeriveRunCoordinator
from pixelpast.persistence.repositories import AlbumAggregateRepository
from pixelpast.shared.progress import JobProgressCallback
from pixelpast.shared.runtime import RuntimeContext


@dataclass(slots=True, frozen=True)
class AlbumAggregateJobResult:
    """Summary returned by the album aggregate derive job."""

    run_id: int
    mode: str
    status: str
    folder_row_count: int
    collection_row_count: int
    asset_evidence_count: int
    person_group_count: int


class AlbumAggregateJob:
    """Rebuild album-level person-group relevance rows from canonical data."""

    def __init__(
        self,
        *,
        loader: AlbumAggregateCanonicalLoader | None = None,
        snapshot_builder: (
            Callable[[AlbumAggregateCanonicalInputs], AlbumAggregateBuildResult] | None
        ) = None,
        persister: AlbumAggregateSnapshotPersister | None = None,
        lifecycle: DeriveRunCoordinator | None = None,
    ) -> None:
        self._loader = loader or AlbumAggregateCanonicalLoader()
        self._snapshot_builder = snapshot_builder or build_album_aggregate_snapshots
        self._persister = persister or AlbumAggregateSnapshotPersister()
        self._lifecycle = lifecycle or DeriveRunCoordinator()

    def run(
        self,
        *,
        runtime: RuntimeContext,
        start_date: date | None = None,
        end_date: date | None = None,
        progress_callback: JobProgressCallback | None = None,
    ) -> AlbumAggregateJobResult:
        """Rebuild the full album aggregate materialization."""

        if start_date is not None or end_date is not None:
            raise ValueError(
                "Album aggregate derivation does not support --start-date/--end-date."
            )

        run_id = self._lifecycle.create_run(
            runtime=runtime,
            job=ALBUM_AGGREGATE_JOB_NAME,
            mode="full",
        )
        progress = AlbumAggregateProgressTracker(
            run_id=run_id,
            runtime=runtime,
            callback=progress_callback,
        )
        session = runtime.session_factory()
        repository = AlbumAggregateRepository(session)

        try:
            progress.start_loading()
            folder_nodes = self._loader.load_folder_nodes(repository=repository)
            progress.mark_loading_bucket_completed()
            collection_nodes = self._loader.load_collection_nodes(repository=repository)
            progress.mark_loading_bucket_completed()
            asset_evidence = self._loader.load_asset_evidence(repository=repository)
            progress.mark_loading_bucket_completed()
            collection_memberships = self._loader.load_collection_memberships(
                repository=repository
            )
            progress.mark_loading_bucket_completed()
            person_groups = self._loader.load_person_groups(repository=repository)
            progress.mark_loading_bucket_completed()
            progress.finish_phase()

            inputs = AlbumAggregateCanonicalInputs(
                folder_nodes=folder_nodes,
                collection_nodes=collection_nodes,
                asset_evidence=asset_evidence,
                collection_memberships=collection_memberships,
                person_groups=person_groups,
            )
            total_input_count = (
                len(folder_nodes)
                + len(collection_nodes)
                + len(asset_evidence)
                + len(collection_memberships)
                + len(person_groups)
            )

            progress.start_building(total_input_count=total_input_count)
            build_result = self._snapshot_builder(inputs)
            progress.mark_build_completed(total_input_count=total_input_count)
            progress.finish_phase()

            total_row_count = (
                len(build_result.folder_rows) + len(build_result.collection_rows)
            )
            progress.start_persisting(total_row_count=total_row_count)
            persistence_result = self._persister.persist(
                repository=repository,
                build_result=build_result,
            )
            session.commit()
            progress.mark_persisted(total_row_count=total_row_count)
            progress.finish_phase()
            progress.finish_run(status="completed")
            return _build_result(
                run_id=run_id,
                persistence_result=persistence_result,
                asset_evidence_count=len(asset_evidence),
                person_group_count=len(person_groups),
            )
        except Exception:
            session.rollback()
            progress.fail_run()
            raise
        finally:
            session.close()


def _build_result(
    *,
    run_id: int,
    persistence_result: AlbumAggregatePersistenceResult,
    asset_evidence_count: int,
    person_group_count: int,
) -> AlbumAggregateJobResult:
    return AlbumAggregateJobResult(
        run_id=run_id,
        mode="full",
        status="completed",
        folder_row_count=persistence_result.folder_row_count,
        collection_row_count=persistence_result.collection_row_count,
        asset_evidence_count=asset_evidence_count,
        person_group_count=person_group_count,
    )
