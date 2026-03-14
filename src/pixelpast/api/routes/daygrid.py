"""Routes for exploration-oriented day-grid reads."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from pixelpast.api.providers import TimelineProjectionProvider
from pixelpast.api.routes.shared import (
    build_exploration_grid_filters,
    get_timeline_projection_provider,
    validate_optional_range,
)
from pixelpast.api.schemas import ExplorationGridResponse

router = APIRouter(tags=["timeline"])


@router.get("/exploration", response_model=ExplorationGridResponse)
def get_exploration(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    view_mode: str = Query(default="activity"),
    person_ids: list[int] = Query(default=[]),
    tag_paths: list[str] = Query(default=[]),
    location_geometry: str | None = Query(default=None),
    distance_latitude: float | None = Query(default=None),
    distance_longitude: float | None = Query(default=None),
    distance_radius_meters: int | None = Query(default=None, ge=1),
    filename_query: str | None = Query(default=None),
    provider: TimelineProjectionProvider = Depends(get_timeline_projection_provider),
) -> ExplorationGridResponse:
    """Return derived-only dense grid activity with server-owned filters."""

    validate_optional_range(start=start, end=end)
    filters = build_exploration_grid_filters(
        view_mode=view_mode,
        person_ids=person_ids,
        tag_paths=tag_paths,
        location_geometry=location_geometry,
        distance_latitude=distance_latitude,
        distance_longitude=distance_longitude,
        distance_radius_meters=distance_radius_meters,
        filename_query=filename_query,
    )
    return provider.get_exploration_grid(
        start=start,
        end=end,
        today=date.today(),
        filters=filters,
    )
