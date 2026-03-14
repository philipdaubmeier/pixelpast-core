"""Daily aggregate derivation job.

The initial v1 score intentionally stays simple and transparent:

    activity_score = total_events + media_count

This weights canonical events and media assets equally and keeps the first
heatmap implementation deterministic and easy to reason about.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date

from pixelpast.persistence.repositories import (
    CanonicalTimelineRepository,
    DailyAggregateRepository,
    DailyAggregateSnapshot,
)
from pixelpast.shared.runtime import RuntimeContext

_SCORE_METADATA = {
    "score_version": "v1",
    "score_formula": "activity_score = total_events + media_count",
}


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
            event_dates = canonical_repository.list_event_dates(
                start_date=start_date,
                end_date=end_date,
            )
            asset_dates = canonical_repository.list_asset_dates(
                start_date=start_date,
                end_date=end_date,
            )
            aggregates = _build_snapshots(
                event_dates=event_dates,
                asset_dates=asset_dates,
            )

            if start_date is None and end_date is None:
                aggregate_repository.replace_all(aggregates=aggregates)
                mode = "full"
                resolved_start_date = min(
                    (aggregate.date for aggregate in aggregates),
                    default=None,
                )
                resolved_end_date = max(
                    (aggregate.date for aggregate in aggregates),
                    default=None,
                )
            else:
                aggregate_repository.replace_range(
                    start_date=start_date,
                    end_date=end_date,
                    aggregates=aggregates,
                )
                mode = "range"
                resolved_start_date = start_date
                resolved_end_date = end_date

            session.commit()
            return DailyAggregateJobResult(
                mode=mode,
                start_date=resolved_start_date,
                end_date=resolved_end_date,
                aggregate_count=len(aggregates),
                total_events=len(event_dates),
                media_count=len(asset_dates),
            )
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def _build_snapshots(
    *,
    event_dates: list[date],
    asset_dates: list[date],
) -> list[DailyAggregateSnapshot]:
    """Build sorted repository snapshots from canonical UTC dates."""

    event_counter = Counter(event_dates)
    asset_counter = Counter(asset_dates)
    aggregate_dates = sorted(set(event_counter) | set(asset_counter))

    return [
        DailyAggregateSnapshot(
            date=aggregate_date,
            total_events=event_counter[aggregate_date],
            media_count=asset_counter[aggregate_date],
            activity_score=_calculate_activity_score(
                total_events=event_counter[aggregate_date],
                media_count=asset_counter[aggregate_date],
            ),
            tag_summary_json=[],
            person_summary_json=[],
            location_summary_json=[],
            metadata_json=dict(_SCORE_METADATA),
        )
        for aggregate_date in aggregate_dates
    ]


def _calculate_activity_score(*, total_events: int, media_count: int) -> int:
    """Return the documented v1 score for a single day."""

    return total_events + media_count


def _validate_date_range(*, start_date: date | None, end_date: date | None) -> None:
    """Ensure the job runs either in full rebuild mode or with a closed range."""

    if (start_date is None) != (end_date is None):
        raise ValueError(
            "Daily aggregate derivation requires both start_date and end_date "
            "when running a range recomputation."
        )

    if start_date is not None and end_date is not None and start_date > end_date:
        raise ValueError("Daily aggregate derivation requires start_date <= end_date.")
