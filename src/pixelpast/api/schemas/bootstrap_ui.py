"""Schemas for exploration bootstrap UI payloads."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class ExplorationRange(BaseModel):
    """Resolved inclusive date range for exploration responses."""

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


class ExplorationBootstrapResponse(BaseModel):
    """Lightweight shell metadata for exploration initialization."""

    range: ExplorationRange
    view_modes: list[ExplorationViewMode]
    persons: list[ExplorationPerson]
    tags: list[ExplorationTag]
