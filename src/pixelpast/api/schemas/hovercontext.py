"""Schemas for hover-context timeline payloads."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from pixelpast.api.schemas.bootstrap_ui import (
    ExplorationPerson,
    ExplorationRange,
    ExplorationTag,
)


class DayContextMapPoint(BaseModel):
    """Serialized real-world map point for one UTC day."""

    id: str | None = None
    label: str | None = None
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
