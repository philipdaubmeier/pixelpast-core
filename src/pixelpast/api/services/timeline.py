"""Service layer for timeline-oriented read endpoints."""

from __future__ import annotations

from datetime import date

from pixelpast.api.schemas import (
    DayAssetItem,
    DayDetailResponse,
    DayEventItem,
    HeatmapDay,
    HeatmapResponse,
)
from pixelpast.persistence.repositories import (
    DailyAggregateReadRepository,
    DayTimelineItemSnapshot,
    DayTimelineRepository,
)


class TimelineQueryService:
    """Compose read repositories into explicit API response models."""

    def __init__(
        self,
        *,
        daily_aggregate_repository: DailyAggregateReadRepository,
        day_timeline_repository: DayTimelineRepository,
    ) -> None:
        self._daily_aggregate_repository = daily_aggregate_repository
        self._day_timeline_repository = day_timeline_repository

    def get_heatmap(self, *, start: date, end: date) -> HeatmapResponse:
        """Return the heatmap projection for an inclusive date range."""

        aggregates = self._daily_aggregate_repository.list_range(
            start_date=start,
            end_date=end,
        )
        return HeatmapResponse(
            start=start,
            end=end,
            days=[
                HeatmapDay(
                    date=aggregate.date,
                    total_events=aggregate.total_events,
                    media_count=aggregate.media_count,
                    activity_score=aggregate.activity_score,
                )
                for aggregate in aggregates
            ],
        )

    def get_day_detail(self, *, day: date) -> DayDetailResponse:
        """Return a unified, time-ordered day projection."""

        snapshots = self._day_timeline_repository.list_day(day=day)
        return DayDetailResponse(
            date=day,
            items=[self._map_day_item(snapshot) for snapshot in snapshots],
        )

    def _map_day_item(
        self,
        snapshot: DayTimelineItemSnapshot,
    ) -> DayEventItem | DayAssetItem:
        """Map repository snapshots to discriminated API items."""

        if snapshot.item_type == "event":
            return DayEventItem(
                item_type="event",
                id=snapshot.id,
                timestamp=snapshot.timestamp,
                event_type=snapshot.type,
                title=snapshot.title,
                summary=snapshot.summary,
            )

        return DayAssetItem(
            item_type="asset",
            id=snapshot.id,
            timestamp=snapshot.timestamp,
            media_type=snapshot.type,
            external_id=snapshot.external_id,
        )
