"""Routes for social-graph projection reads."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from pixelpast.api.providers import SocialGraphProjectionProvider
from pixelpast.api.routes.shared import (
    build_social_graph_filters,
    get_social_graph_projection_provider,
    validate_optional_range,
)
from pixelpast.api.schemas import SocialGraphResponse

router = APIRouter(tags=["social"])


@router.get("/social/graph", response_model=SocialGraphResponse)
def get_social_graph(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    person_ids: list[int] = Query(default=[]),
    max_people_per_asset: int = Query(default=10, ge=2, le=30),
    tag_paths: list[str] = Query(default=[]),
    location_geometry: str | None = Query(default=None),
    distance_latitude: float | None = Query(default=None),
    distance_longitude: float | None = Query(default=None),
    distance_radius_meters: int | None = Query(default=None, ge=1),
    filename_query: str | None = Query(default=None),
    provider: SocialGraphProjectionProvider = Depends(
        get_social_graph_projection_provider
    ),
) -> SocialGraphResponse:
    """Return the social graph filtered by date range and person selection only."""

    validate_optional_range(start=start, end=end)
    filters = build_social_graph_filters(
        person_ids=person_ids,
        max_people_per_asset=max_people_per_asset,
        tag_paths=tag_paths,
        location_geometry=location_geometry,
        distance_latitude=distance_latitude,
        distance_longitude=distance_longitude,
        distance_radius_meters=distance_radius_meters,
        filename_query=filename_query,
    )
    return provider.get_social_graph(
        start=start,
        end=end,
        today=date.today(),
        filters=filters,
    )
