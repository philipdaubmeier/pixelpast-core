"""Schemas for single-day timeline detail payloads."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field


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
