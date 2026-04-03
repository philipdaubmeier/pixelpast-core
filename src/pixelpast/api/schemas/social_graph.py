"""Schemas for social-graph projection payloads."""

from __future__ import annotations

from pydantic import BaseModel


class SocialGraphPersonGroup(BaseModel):
    """Matching person-group metadata exposed for one social-graph node."""

    id: int
    name: str
    color_index: int | None = None


class SocialGraphPerson(BaseModel):
    """Person node exposed by the social-graph API contract."""

    id: int
    name: str
    occurrence_count: int
    matching_groups: list[SocialGraphPersonGroup]


class SocialGraphLink(BaseModel):
    """Weighted unordered person-pair edge in the social graph."""

    person_ids: list[int]
    weight: int
    affinity: float


class SocialGraphResponse(BaseModel):
    """Canonical social-graph projection response."""

    persons: list[SocialGraphPerson]
    links: list[SocialGraphLink]
