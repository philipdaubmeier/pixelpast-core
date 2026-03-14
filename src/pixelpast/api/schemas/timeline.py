"""Read-oriented schemas for temporal exploration endpoints."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


ColorValue = Literal["empty", "low", "medium", "high"]


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


class ExplorationRange(BaseModel):
    """Resolved inclusive date range for exploration bootstrap."""

    start: date
    end: date


class ExplorationViewMode(BaseModel):
    """Backend-defined exploration view mode metadata."""

    id: str
    label: str
    description: str


class ExplorationPerson(BaseModel):
    """Person item used by the exploration shell."""

    id: int
    name: str
    role: str | None


class ExplorationTag(BaseModel):
    """Tag item used by the exploration shell."""

    path: str
    label: str


class ExplorationDayTagSummary(BaseModel):
    """Derived tag summary attached to one explored day."""

    path: str
    label: str
    count: int


class ExplorationDayPersonSummary(BaseModel):
    """Derived person summary attached to one explored day."""

    person_id: int
    name: str
    role: str | None
    count: int


class ExplorationDayLocationSummary(BaseModel):
    """Derived location summary attached to one explored day."""

    label: str
    latitude: float
    longitude: float
    count: int


class ExplorationDayDerivedSummary(BaseModel):
    """Derived semantic rollup for one explored day."""

    tags: list[ExplorationDayTagSummary]
    persons: list[ExplorationDayPersonSummary]
    locations: list[ExplorationDayLocationSummary]
    metadata: dict[str, Any]


class ExplorationDaySourceSummary(BaseModel):
    """Connector-scoped derived summary for one explored day."""

    source_type: str
    event_count: int
    asset_count: int
    activity_score: int
    color_value: ColorValue
    has_data: bool
    person_ids: list[int]
    tag_paths: list[str]
    derived_summary: ExplorationDayDerivedSummary


class ExplorationDay(BaseModel):
    """Dense exploration day payload for the calendar grid."""

    date: date
    event_count: int
    asset_count: int
    activity_score: int
    color_value: ColorValue
    has_data: bool
    person_ids: list[int]
    tag_paths: list[str]
    derived_summary: ExplorationDayDerivedSummary
    source_summaries: list[ExplorationDaySourceSummary]


class ExplorationResponse(BaseModel):
    """Bootstrap projection for the exploration shell."""

    range: ExplorationRange
    view_modes: list[ExplorationViewMode]
    persons: list[ExplorationPerson]
    tags: list[ExplorationTag]
    days: list[ExplorationDay]


class DayContextMapPoint(BaseModel):
    """Serialized real-world map point for one UTC day."""

    id: str
    label: str
    latitude: float
    longitude: float


class DayContextSummaryCounts(BaseModel):
    """Lightweight per-day counts for hover context panels."""

    events: int
    assets: int
    places: int


class DayContextDay(BaseModel):
    """Dense hover-context payload for one UTC calendar day."""

    date: date
    persons: list[ExplorationPerson]
    tags: list[ExplorationTag]
    map_points: list[DayContextMapPoint]
    summary_counts: DayContextSummaryCounts


class DayContextResponse(BaseModel):
    """Serialized response for an inclusive day-context preload range."""

    range: ExplorationRange
    days: list[DayContextDay]


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
