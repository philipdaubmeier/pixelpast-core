"""Routes for exploration-oriented day-grid reads."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from pixelpast.api.providers import TimelineProjectionProvider
from pixelpast.api.routes.metadata import (
    BAD_REQUEST_RESPONSE,
    VALIDATION_ERROR_RESPONSE,
    combine_responses,
)
from pixelpast.api.routes.shared import (
    build_exploration_grid_filters,
    get_timeline_projection_provider,
    validate_optional_range,
)
from pixelpast.api.schemas import ExplorationGridResponse

router = APIRouter(tags=["timeline"])


@router.get(
    "/exploration",
    response_model=ExplorationGridResponse,
    response_model_exclude_none=True,
    summary="Get exploration day grid",
    description=(
        "Return the dense exploration day grid for the resolved inclusive UTC "
        "date range. Optional server-side filters constrain which canonical "
        "items contribute to each day."
    ),
    response_description="Dense exploration grid for the resolved UTC date range.",
    responses=combine_responses(BAD_REQUEST_RESPONSE, VALIDATION_ERROR_RESPONSE),
)
def get_exploration(
    start: date | None = Query(
        default=None,
        description=(
            "Inclusive UTC start date for the requested exploration window. "
            "Must be provided together with end."
        ),
    ),
    end: date | None = Query(
        default=None,
        description=(
            "Inclusive UTC end date for the requested exploration window. "
            "Must be provided together with start."
        ),
    ),
    view_mode: str = Query(
        default="activity",
        description=(
            "Backend-defined daily view identifier that determines which "
            "derived day rows are projected into the grid."
        ),
    ),
    person_ids: list[int] = Query(
        default=[],
        description=(
            "Repeatable person identifiers. Only canonical items linked to at "
            "least one selected person contribute to counts."
        ),
    ),
    tag_paths: list[str] = Query(
        default=[],
        description=(
            "Repeatable normalized tag paths used to restrict contributing "
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
    provider: TimelineProjectionProvider = Depends(get_timeline_projection_provider),
) -> ExplorationGridResponse:
    """Return derived-only dense grid activity with server-owned filters."""

    validate_optional_range(start=start, end=end)
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
    return provider.get_exploration_grid(
        start=start,
        end=end,
        today=date.today(),
        filters=filters,
    )
