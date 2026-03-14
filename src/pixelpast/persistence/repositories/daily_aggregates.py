"""Repositories for canonical daily aggregate derivation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from pixelpast.persistence.models import (
    Asset,
    DAILY_AGGREGATE_OVERALL_SOURCE_TYPE,
    DAILY_AGGREGATE_SCOPE_OVERALL,
    DailyAggregate,
    Event,
)


@dataclass(slots=True, frozen=True)
class DailyAggregateSnapshot:
    """Serializable repository payload for a derived day summary."""

    date: date
    total_events: int
    media_count: int
    activity_score: int
    tag_summary_json: list[dict[str, Any]]
    person_summary_json: list[dict[str, Any]]
    location_summary_json: list[dict[str, Any]]
    metadata_json: dict[str, Any]
    aggregate_scope: str = DAILY_AGGREGATE_SCOPE_OVERALL
    source_type: str = DAILY_AGGREGATE_OVERALL_SOURCE_TYPE


class CanonicalTimelineRepository:
    """Read canonical timestamps used to build day-level summaries."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_event_dates(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[date]:
        """Return UTC calendar dates for canonical events in the requested range."""

        statement = _apply_datetime_range(
            select(Event.timestamp_start),
            column=Event.timestamp_start,
            start_date=start_date,
            end_date=end_date,
        )
        timestamps = self._session.execute(statement).scalars()
        return [timestamp.date() for timestamp in timestamps]

    def list_asset_dates(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[date]:
        """Return UTC calendar dates for canonical assets in the requested range."""

        statement = _apply_datetime_range(
            select(Asset.timestamp),
            column=Asset.timestamp,
            start_date=start_date,
            end_date=end_date,
        )
        timestamps = self._session.execute(statement).scalars()
        return [timestamp.date() for timestamp in timestamps]


class DailyAggregateRepository:
    """Persist derived daily aggregate rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def replace_all(self, *, aggregates: list[DailyAggregateSnapshot]) -> None:
        """Delete all existing aggregate rows and replace them atomically."""

        self._session.execute(delete(DailyAggregate))
        self._insert(aggregates)

    def replace_range(
        self,
        *,
        start_date: date,
        end_date: date,
        aggregates: list[DailyAggregateSnapshot],
    ) -> None:
        """Delete and replace aggregate rows for an inclusive date window."""

        self._session.execute(
            delete(DailyAggregate).where(
                DailyAggregate.date >= start_date,
                DailyAggregate.date <= end_date,
            )
        )
        self._insert(aggregates)

    def _insert(self, aggregates: list[DailyAggregateSnapshot]) -> None:
        """Insert repository snapshots as ORM rows."""

        if not aggregates:
            return

        self._session.add_all(
            DailyAggregate(
                date=aggregate.date,
                aggregate_scope=aggregate.aggregate_scope,
                source_type=aggregate.source_type,
                total_events=aggregate.total_events,
                media_count=aggregate.media_count,
                activity_score=aggregate.activity_score,
                tag_summary_json=list(aggregate.tag_summary_json),
                person_summary_json=list(aggregate.person_summary_json),
                location_summary_json=list(aggregate.location_summary_json),
                metadata_json=dict(aggregate.metadata_json),
            )
            for aggregate in aggregates
        )


def _apply_datetime_range(
    statement,
    *,
    column,
    start_date: date | None,
    end_date: date | None,
):
    """Apply an inclusive UTC date range to a timestamp column."""

    if start_date is not None:
        statement = statement.where(
            column >= datetime.combine(start_date, time.min, tzinfo=UTC)
        )

    if end_date is not None:
        statement = statement.where(
            column
            < datetime.combine(
                end_date + timedelta(days=1),
                time.min,
                tzinfo=UTC,
            )
        )

    return statement
