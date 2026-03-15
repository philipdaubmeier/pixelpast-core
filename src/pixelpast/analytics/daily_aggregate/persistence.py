"""Persistence orchestration for daily aggregate snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from pixelpast.persistence.repositories.daily_aggregates import (
    DailyAggregateRepository,
    DailyAggregateSnapshot,
)


@dataclass(slots=True, frozen=True)
class DailyAggregatePersistenceResult:
    """Resolved persistence mode and effective rebuilt date bounds."""

    mode: str
    start_date: date | None
    end_date: date | None


class DailyAggregateSnapshotPersister:
    """Choose the appropriate repository persistence mode for a job run."""

    def persist(
        self,
        *,
        repository: DailyAggregateRepository,
        start_date: date | None,
        end_date: date | None,
        aggregates: list[DailyAggregateSnapshot],
    ) -> DailyAggregatePersistenceResult:
        """Replace all rows or one inclusive range based on the requested window."""

        if start_date is None and end_date is None:
            repository.replace_all(aggregates=aggregates)
            return DailyAggregatePersistenceResult(
                mode="full",
                start_date=min(
                    (aggregate.date for aggregate in aggregates),
                    default=None,
                ),
                end_date=max(
                    (aggregate.date for aggregate in aggregates),
                    default=None,
                ),
            )

        repository.replace_range(
            start_date=start_date,
            end_date=end_date,
            aggregates=aggregates,
        )
        return DailyAggregatePersistenceResult(
            mode="range",
            start_date=start_date,
            end_date=end_date,
        )
