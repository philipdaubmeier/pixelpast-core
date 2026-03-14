"""Schemas for day-grid and heatmap exploration payloads."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

from pixelpast.api.schemas.bootstrap_ui import ExplorationRange


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


class ExplorationGridDay(BaseModel):
    """Minimal derived activity payload for one calendar day."""

    date: date
    activity_score: int
    color_value: ColorValue
    has_data: bool


class ExplorationGridResponse(BaseModel):
    """Derived-only dense grid response for an inclusive date range."""

    range: ExplorationRange
    days: list[ExplorationGridDay]
