"""Album-level aggregate derive job package."""

from pixelpast.analytics.album_aggregate.builder import (
    AlbumAggregateBuildResult,
    build_album_aggregate_snapshots,
)
from pixelpast.analytics.album_aggregate.job import (
    ALBUM_AGGREGATE_JOB_NAME,
    AlbumAggregateJob,
    AlbumAggregateJobResult,
)
from pixelpast.analytics.album_aggregate.loading import AlbumAggregateCanonicalInputs

__all__ = [
    "ALBUM_AGGREGATE_JOB_NAME",
    "AlbumAggregateBuildResult",
    "AlbumAggregateCanonicalInputs",
    "AlbumAggregateJob",
    "AlbumAggregateJobResult",
    "build_album_aggregate_snapshots",
]
