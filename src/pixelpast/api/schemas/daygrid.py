"""Schemas for exploration day-grid payloads."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

from pixelpast.api.schemas.bootstrap_ui import ExplorationRange


ColorValue = Literal["empty", "low", "medium", "high"]


class ExplorationGridDay(BaseModel):
    """Minimal derived activity payload for one calendar day."""

    date: date
    count: int
    activity_score: int
    color_value: ColorValue
    has_data: bool


class ExplorationGridResponse(BaseModel):
    """Derived-only dense grid response for an inclusive date range."""

    range: ExplorationRange
    days: list[ExplorationGridDay]
