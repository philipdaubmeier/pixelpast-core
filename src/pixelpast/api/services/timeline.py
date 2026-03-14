"""Service layer for timeline-oriented read endpoints."""

from __future__ import annotations

from datetime import date

from pixelpast.api.schemas import (
    DayAssetItem,
    DayDetailResponse,
    DayEventItem,
)
from pixelpast.persistence.repositories import (
    DayTimelineItemSnapshot,
    DayTimelineRepository,
)


class TimelineQueryService:
    """Compose read repositories into explicit API response models."""

    def __init__(
        self,
        *,
        day_timeline_repository: DayTimelineRepository,
    ) -> None:
        self._day_timeline_repository = day_timeline_repository

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
