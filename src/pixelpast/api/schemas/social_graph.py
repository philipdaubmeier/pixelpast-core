"""Schemas for social-graph projection payloads."""

from __future__ import annotations

from pydantic import BaseModel


class SocialGraphPerson(BaseModel):
    """Person node exposed by the social-graph API contract."""

    id: int
    name: str
    occurrence_count: int


class SocialGraphLink(BaseModel):
    """Weighted unordered person-pair edge in the social graph."""

    person_ids: list[int]
    weight: int


class SocialGraphResponse(BaseModel):
    """Canonical social-graph projection response."""

    persons: list[SocialGraphPerson]
    links: list[SocialGraphLink]
