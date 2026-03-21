"""Routes for hover-context timeline data."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from pixelpast.api.dependencies import get_app_settings
from pixelpast.api.providers import TimelineProjectionProvider
from pixelpast.api.routes.metadata import (
    BAD_REQUEST_RESPONSE,
    VALIDATION_ERROR_RESPONSE,
    combine_responses,
)
from pixelpast.api.routes.shared import (
    build_exploration_grid_filters,
    get_timeline_projection_provider,
)
from pixelpast.api.schemas import DayContextResponse
from pixelpast.shared.settings import Settings

router = APIRouter(tags=["timeline"])


@router.get(
    "/days/context",
    response_model=DayContextResponse,
    summary="Get day context preload",
    description=(
        "Return per-day context panels for an inclusive UTC range so the UI "
        "can preload hover data, tags, people, map points, and summary counts."
    ),
    response_description="Dense day-context payload for the requested UTC range.",
    responses=combine_responses(BAD_REQUEST_RESPONSE, VALIDATION_ERROR_RESPONSE),
)
def get_day_context(
    start: date = Query(
        ...,
        description="Inclusive UTC start date for the requested context preload.",
    ),
    end: date = Query(
        ...,
        description="Inclusive UTC end date for the requested context preload.",
    ),
    view_mode: str = Query(
        default="activity",
        description=(
            "Backend-defined daily view identifier that determines which "
            "derived day rows provide the context payload."
        ),
    ),
    person_ids: list[int] = Query(
        default=[],
        description=(
            "Repeatable person identifiers used to filter contributing "
            "canonical items."
        ),
    ),
    tag_paths: list[str] = Query(
        default=[],
        description=(
            "Repeatable normalized tag paths used to filter contributing "
            "canonical items."
        ),
    ),
    location_geometry: str | None = Query(
        default=None,
        description=(
            "Optional serialized geometry filter interpreted by the active "
            "projection provider."
        ),
    ),
    distance_latitude: float | None = Query(
        default=None,
        ge=-90,
        le=90,
        description=(
            "Latitude for a radial distance filter. Use together with "
            "distance_longitude and distance_radius_meters."
        ),
    ),
    distance_longitude: float | None = Query(
        default=None,
        ge=-180,
        le=180,
        description=(
            "Longitude for a radial distance filter. Use together with "
            "distance_latitude and distance_radius_meters."
        ),
    ),
    distance_radius_meters: int | None = Query(
        default=None,
        ge=1,
        description="Radius in meters for the radial distance filter.",
    ),
    filename_query: str | None = Query(
        default=None,
        min_length=1,
        description=(
            "Case-insensitive filename search term applied to contributing "
            "assets."
        ),
    ),
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
