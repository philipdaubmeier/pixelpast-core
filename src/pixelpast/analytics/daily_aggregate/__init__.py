"""Daily aggregate derivation job package."""

from pixelpast.analytics.daily_aggregate.builder import (
    build_daily_aggregate_snapshots,
)
from pixelpast.analytics.daily_aggregate.job import (
    DailyAggregateJob,
    DailyAggregateJobResult,
)
from pixelpast.analytics.daily_aggregate.loading import (
    DailyAggregateCanonicalInputs,
)

__all__ = [
    "DailyAggregateCanonicalInputs",
    "DailyAggregateJob",
    "DailyAggregateJobResult",
    "build_daily_aggregate_snapshots",
]
