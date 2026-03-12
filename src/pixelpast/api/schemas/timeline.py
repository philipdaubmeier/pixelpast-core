"""Read-oriented schemas for temporal exploration endpoints."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class HeatmapDay(BaseModel):
    """Serialized per-day heatmap payload."""

    date: date
    total_events: int
    media_count: int
    activity_score: int


class HeatmapResponse(BaseModel):
    """Serialized heatmap response for an inclusive date range."""

    start: date
    end: date
    days: list[HeatmapDay]


class DayEventItem(BaseModel):
    """Serialized day-detail item for a canonical event."""

    item_type: Literal["event"]
    id: int
    timestamp: datetime
    event_type: str
    title: str
    summary: str | None


class DayAssetItem(BaseModel):
    """Serialized day-detail item for a canonical asset."""

    item_type: Literal["asset"]
    id: int
    timestamp: datetime
    media_type: str
    external_id: str


DayTimelineItem = Annotated[
    DayEventItem | DayAssetItem,
    Field(discriminator="item_type"),
]


class DayDetailResponse(BaseModel):
    """Serialized response for a single UTC calendar day."""

    date: date
    items: list[DayTimelineItem]
