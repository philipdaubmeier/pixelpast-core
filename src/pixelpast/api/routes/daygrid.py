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

EXPLORATION_GRID_SUCCESS_EXAMPLES = {
    "filtered_travel_grid": {
        "summary": "Day grid filtered to one person and a travel tag",
        "value": {
            "range": {"start": "2026-07-01", "end": "2026-07-07"},
            "days": [
                {"date": "2026-07-01", "count": 0, "color": "empty"},
                {
                    "date": "2026-07-02",
                    "count": 3,
                    "color": "medium",
                    "label": "Venice arrival and evening walk",
                },
                {
                    "date": "2026-07-03",
                    "count": 6,
                    "color": "#E07A5F",
                    "label": "Biennale and canal photos",
                },
            ],
        },
    }
}


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
    responses=combine_responses(
        {
            200: {
                "content": {
                    "application/json": {
                        "examples": EXPLORATION_GRID_SUCCESS_EXAMPLES,
                    }
                }
            }
        },
        BAD_REQUEST_RESPONSE,
        VALIDATION_ERROR_RESPONSE,
    ),
)
def get_exploration(
    start: date | None = Query(
        default=None,
        description=(
            "Inclusive UTC start date for the requested exploration window. "
            "Must be provided together with end."
        ),
        openapi_examples={
            "trip_window_start": {
                "summary": "Trip window start",
                "value": "2026-07-01",
            }
        },
    ),
    end: date | None = Query(
        default=None,
        description=(
            "Inclusive UTC end date for the requested exploration window. "
            "Must be provided together with start."
        ),
        openapi_examples={
            "trip_window_end": {
                "summary": "Trip window end",
                "value": "2026-07-07",
            }
        },
    ),
    view_mode: str = Query(
        default="activity",
        description=(
            "Backend-defined daily view identifier that determines which "
            "derived day rows are projected into the grid."
        ),
        openapi_examples={
            "travel_view": {
                "summary": "Default activity projection",
                "value": "activity",
            }
        },
    ),
    person_ids: list[int] = Query(
        default=[],
        description=(
            "Repeatable person identifiers. Only canonical items linked to at "
            "least one selected person contribute to counts."
        ),
        openapi_examples={
            "anna": {
                "summary": "Filter to Anna Becker",
                "value": 7,
            }
        },
    ),
    tag_paths: list[str] = Query(
        default=[],
        description=(
            "Repeatable normalized tag paths used to restrict contributing "
            "canonical items."
        ),
        openapi_examples={
            "venice": {
                "summary": "Filter to a travel tag subtree",
                "value": "travel/italy/venice",
            }
        },
    ),
    location_geometry: str | None = Query(
        default=None,
        description=(
            "Optional serialized geometry filter interpreted by the active "
            "projection provider."
        ),
        openapi_examples={
            "venice_bbox": {
                "summary": "Serialized geometry understood by the active provider",
                "value": "bbox:12.285,45.423,12.380,45.465",
            }
        },
    ),
    distance_latitude: float | None = Query(
        default=None,
        ge=-90,
        le=90,
        description=(
            "Latitude for a radial distance filter. Use together with "
            "distance_longitude and distance_radius_meters."
        ),
        openapi_examples={
            "venice_center": {
                "summary": "Latitude for a nearby-place filter",
                "value": 45.4371,
            }
        },
    ),
    distance_longitude: float | None = Query(
        default=None,
        ge=-180,
        le=180,
        description=(
            "Longitude for a radial distance filter. Use together with "
            "distance_latitude and distance_radius_meters."
        ),
        openapi_examples={
            "venice_center": {
                "summary": "Longitude for a nearby-place filter",
                "value": 12.3327,
            }
        },
    ),
    distance_radius_meters: int | None = Query(
        default=None,
        ge=1,
        description="Radius in meters for the radial distance filter.",
        openapi_examples={
            "walkable_radius": {
                "summary": "Five kilometer radial filter",
                "value": 5000,
            }
        },
    ),
    filename_query: str | None = Query(
        default=None,
        min_length=1,
        description=(
            "Case-insensitive filename search term applied to contributing "
            "assets."
        ),
        openapi_examples={
            "camera_roll": {
                "summary": "Filename substring match",
                "value": "IMG_20260703",
            }
        },
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
