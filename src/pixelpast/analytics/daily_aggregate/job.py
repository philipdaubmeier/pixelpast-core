"""Daily aggregate derive job composition root."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from pixelpast.analytics.daily_aggregate.builder import (
    build_daily_aggregate_snapshots,
)
from pixelpast.analytics.daily_aggregate.loading import (
    DailyAggregateCanonicalInputs,
    DailyAggregateCanonicalLoader,
)
from pixelpast.analytics.daily_aggregate.persistence import (
    DailyAggregateSnapshotPersister,
)
from pixelpast.persistence.repositories.daily_aggregates import (
    CanonicalTimelineRepository,
    DailyAggregateRepository,
    DailyAggregateSnapshot,
)
from pixelpast.shared.runtime import RuntimeContext


@dataclass(slots=True, frozen=True)
class DailyAggregateJobResult:
    """Summary returned by the daily aggregate derivation job."""

    mode: str
    start_date: date | None
    end_date: date | None
    aggregate_count: int
    total_events: int
    media_count: int


class DailyAggregateJob:
    """Rebuild daily aggregate rows from canonical events and assets."""

    def __init__(
        self,
        *,
        loader: DailyAggregateCanonicalLoader | None = None,
        snapshot_builder: (
            Callable[[DailyAggregateCanonicalInputs], list[DailyAggregateSnapshot]]
            | None
        ) = None,
        persister: DailyAggregateSnapshotPersister | None = None,
    ) -> None:
        self._loader = loader or DailyAggregateCanonicalLoader()
        self._snapshot_builder = snapshot_builder or build_daily_aggregate_snapshots
        self._persister = persister or DailyAggregateSnapshotPersister()

    def run(
        self,
        *,
        runtime: RuntimeContext,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> DailyAggregateJobResult:
        """Recompute daily aggregates for a full rebuild or an inclusive range."""

        _validate_date_range(start_date=start_date, end_date=end_date)

        session = runtime.session_factory()
        canonical_repository = CanonicalTimelineRepository(session)
        aggregate_repository = DailyAggregateRepository(session)

        try:
            inputs = self._loader.load(
                repository=canonical_repository,
                start_date=start_date,
                end_date=end_date,
            )
            aggregates = self._snapshot_builder(inputs)
            persistence_result = self._persister.persist(
                repository=aggregate_repository,
                start_date=start_date,
                end_date=end_date,
                aggregates=aggregates,
            )
            session.commit()
            return DailyAggregateJobResult(
                mode=persistence_result.mode,
                start_date=persistence_result.start_date,
                end_date=persistence_result.end_date,
                aggregate_count=len(aggregates),
                total_events=len(inputs.event_inputs),
                media_count=len(inputs.asset_inputs),
            )
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def _validate_date_range(*, start_date: date | None, end_date: date | None) -> None:
    """Ensure the job runs either in full rebuild mode or with a closed range."""

    if (start_date is None) != (end_date is None):
        raise ValueError(
            "Daily aggregate derivation requires both start_date and end_date "
            "when running a range recomputation."
        )

    if start_date is not None and end_date is not None and start_date > end_date:
        raise ValueError("Daily aggregate derivation requires start_date <= end_date.")
