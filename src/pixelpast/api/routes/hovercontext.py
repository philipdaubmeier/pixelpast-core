"""Routes for hover-context timeline data."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from pixelpast.api.dependencies import get_app_settings
from pixelpast.api.providers import TimelineProjectionProvider
from pixelpast.api.routes.shared import (
    build_exploration_grid_filters,
    get_timeline_projection_provider,
)
from pixelpast.api.schemas import DayContextResponse
from pixelpast.shared.settings import Settings

router = APIRouter(tags=["timeline"])


@router.get("/days/context", response_model=DayContextResponse)
def get_day_context(
    start: date = Query(...),
    end: date = Query(...),
    view_mode: str = Query(default="activity"),
    person_ids: list[int] = Query(default=[]),
    tag_paths: list[str] = Query(default=[]),
    location_geometry: str | None = Query(default=None),
    distance_latitude: float | None = Query(default=None),
    distance_longitude: float | None = Query(default=None),
    distance_radius_meters: int | None = Query(default=None, ge=1),
    filename_query: str | None = Query(default=None),
    settings: Settings = Depends(get_app_settings),
    provider: TimelineProjectionProvider = Depends(get_timeline_projection_provider),
) -> DayContextResponse:
    """Return dense hover-context data for an inclusive UTC date range."""

    if start > end:
        raise HTTPException(
            status_code=400,
            detail="start must be less than or equal to end",
        )

    requested_day_count = (end - start).days + 1
    if requested_day_count > settings.day_context_max_days:
        raise HTTPException(
            status_code=400,
            detail=(
                "requested range exceeds maximum day context window of "
                f"{settings.day_context_max_days} days"
            ),
        )

    filters = build_exploration_grid_filters(
        view_mode=view_mode,
        provider=provider,
        person_ids=person_ids,
        tag_paths=tag_paths,
        location_geometry=location_geometry,
        distance_latitude=distance_latitude,
        distance_longitude=distance_longitude,
        distance_radius_meters=distance_radius_meters,
        filename_query=filename_query,
    )
    return provider.get_day_context(start=start, end=end, filters=filters)
