"""Persistence orchestration for album aggregate snapshots."""

from __future__ import annotations

from dataclasses import dataclass

from pixelpast.analytics.album_aggregate.builder import AlbumAggregateBuildResult
from pixelpast.persistence.repositories import AlbumAggregateRepository


@dataclass(slots=True, frozen=True)
class AlbumAggregatePersistenceResult:
    """Result summary for one persisted album aggregate rebuild."""

    folder_row_count: int
    collection_row_count: int


class AlbumAggregateSnapshotPersister:
    """Persist rebuilt album aggregate snapshots through the repository layer."""

    def persist(
        self,
        *,
        repository: AlbumAggregateRepository,
        build_result: AlbumAggregateBuildResult,
    ) -> AlbumAggregatePersistenceResult:
        """Replace the stored album aggregate rows atomically."""

        repository.replace_all(
            folder_rows=build_result.folder_rows,
            collection_rows=build_result.collection_rows,
        )
        return AlbumAggregatePersistenceResult(
            folder_row_count=len(build_result.folder_rows),
            collection_row_count=len(build_result.collection_rows),
        )
