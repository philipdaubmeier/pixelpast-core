"""Read repositories for heatmap and day-detail API projections."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from pixelpast.persistence.models import Asset, DailyAggregate, Event
from pixelpast.persistence.repositories.daily_aggregates import _apply_datetime_range


@dataclass(slots=True, frozen=True)
class DailyAggregateReadSnapshot:
    """Serializable read-model payload for a heatmap day."""

    date: date
    total_events: int
    media_count: int
    activity_score: int


@dataclass(slots=True, frozen=True)
class DayTimelineItemSnapshot:
    """Serializable read-model payload for a day-detail item."""

    item_type: str
    id: int
    timestamp: datetime
    type: str
    title: str | None
    summary: str | None
    external_id: str | None


class DailyAggregateReadRepository:
    """Read derived daily aggregate rows for heatmap endpoints."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_range(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> list[DailyAggregateReadSnapshot]:
        """Return all aggregate rows in an inclusive date range."""

        statement = (
            select(DailyAggregate)
            .where(
                DailyAggregate.date >= start_date,
                DailyAggregate.date <= end_date,
            )
            .order_by(DailyAggregate.date)
        )
        aggregates = self._session.execute(statement).scalars()
        return [
            DailyAggregateReadSnapshot(
                date=aggregate.date,
                total_events=aggregate.total_events,
                media_count=aggregate.media_count,
                activity_score=aggregate.activity_score,
            )
            for aggregate in aggregates
        ]


class DayTimelineRepository:
    """Read canonical events and assets for a unified day view."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_day(self, *, day: date) -> list[DayTimelineItemSnapshot]:
        """Return a single UTC calendar day ordered across events and assets."""

        items = [*self._list_event_items(day=day), *self._list_asset_items(day=day)]
        return sorted(items, key=lambda item: (item.timestamp, item.item_type, item.id))

    def _list_event_items(self, *, day: date) -> list[DayTimelineItemSnapshot]:
        """Return read snapshots for canonical events on the given day."""

        statement = _apply_datetime_range(
            select(Event).order_by(Event.timestamp_start, Event.id),
            column=Event.timestamp_start,
            start_date=day,
            end_date=day,
        )
        events = self._session.execute(statement).scalars()
        return [
            DayTimelineItemSnapshot(
                item_type="event",
                id=event.id,
                timestamp=event.timestamp_start,
                type=event.type,
                title=event.title,
                summary=event.summary,
                external_id=None,
            )
            for event in events
        ]

    def _list_asset_items(self, *, day: date) -> list[DayTimelineItemSnapshot]:
        """Return read snapshots for canonical assets on the given day."""

        statement = _apply_datetime_range(
            select(Asset).order_by(Asset.timestamp, Asset.id),
            column=Asset.timestamp,
            start_date=day,
            end_date=day,
        )
        assets = self._session.execute(statement).scalars()
        return [
            DayTimelineItemSnapshot(
                item_type="asset",
                id=asset.id,
                timestamp=asset.timestamp,
                type=asset.media_type,
                title=None,
                summary=None,
                external_id=asset.external_id,
            )
            for asset in assets
        ]
