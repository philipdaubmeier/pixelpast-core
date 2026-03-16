"""Schemas for exploration day-grid payloads."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from pixelpast.api.schemas.bootstrap_ui import ExplorationRange


ColorToken = Literal["empty", "low", "medium", "high"]
HexColor = Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$")]
ColorValue = ColorToken | HexColor


class ExplorationGridDay(BaseModel):
    """Minimal derived activity payload for one calendar day."""

    date: date
    count: int
    color: ColorValue
    label: str | None = None


class ExplorationGridResponse(BaseModel):
    """Derived-only dense grid response for an inclusive date range."""

    range: ExplorationRange
    days: list[ExplorationGridDay]
