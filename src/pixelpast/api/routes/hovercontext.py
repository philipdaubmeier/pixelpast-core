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

DAY_CONTEXT_SUCCESS_EXAMPLES = {
    "preloaded_trip_week": {
        "summary": "Context preload for a short trip window",
        "value": {
            "range": {"start": "2026-07-01", "end": "2026-07-03"},
            "days": [
                {
                    "date": "2026-07-01",
                    "persons": [],
                    "tags": [],
                    "map_points": [],
                    "summary_counts": {"events": 0, "assets": 0, "places": 0},
                },
                {
                    "date": "2026-07-02",
                    "persons": [
                        {"id": 7, "name": "Anna Becker", "role": "family"},
                        {"id": 12, "name": "Milo Tan", "role": "friend"},
                    ],
                    "tags": [
                        {"path": "travel/italy/venice", "label": "Venice"},
                        {"path": "activity/walking", "label": "Walking"},
                    ],
                    "map_points": [
                        {
                            "id": "location:2026-07-02:1",
                            "label": "Santa Lucia Station",
                            "latitude": 45.4419,
                            "longitude": 12.3211,
                        }
                    ],
                    "summary_counts": {"events": 2, "assets": 1, "places": 1},
                },
            ],
        },
    }
}

DAY_CONTEXT_BAD_REQUEST_EXAMPLES = {
    **BAD_REQUEST_RESPONSE[400]["content"]["application/json"]["examples"],
    "window_limit": {
        "summary": "Requested preload window too large",
        "value": {
            "detail": "requested range exceeds maximum day context window of 31 days"
        },
    },
    "unsupported_view_mode": {
        "summary": "Unknown daily view identifier",
        "value": {"detail": "unsupported view_mode: travel-intensity"},
    },
}


@router.get(
    "/days/context",
    response_model=DayContextResponse,
    summary="Get day context preload",
    description=(
        "Return per-day context panels for an inclusive UTC range so the UI "
        "can preload hover data, tags, people, map points, and summary counts."
    ),
    response_description="Dense day-context payload for the requested UTC range.",
    responses=combine_responses(
        {
            200: {
                "content": {
                    "application/json": {
                        "examples": DAY_CONTEXT_SUCCESS_EXAMPLES,
                    }
                }
            }
        },
        {
            400: {
                **BAD_REQUEST_RESPONSE[400],
                "content": {
                    "application/json": {
                        "examples": DAY_CONTEXT_BAD_REQUEST_EXAMPLES,
                    }
                },
            }
        },
        VALIDATION_ERROR_RESPONSE,
    ),
)
def get_day_context(
    start: date = Query(
        ...,
        description="Inclusive UTC start date for the requested context preload.",
        openapi_examples={
            "trip_window_start": {
                "summary": "Preload start date",
                "value": "2026-07-01",
            }
        },
    ),
    end: date = Query(
        ...,
        description="Inclusive UTC end date for the requested context preload.",
        openapi_examples={
            "trip_window_end": {
                "summary": "Preload end date",
                "value": "2026-07-03",
            }
        },
    ),
    view_mode: str = Query(
        default="activity",
        description=(
            "Backend-defined daily view identifier that determines which "
            "derived day rows provide the context payload."
        ),
        openapi_examples={
            "activity_view": {
                "summary": "Default activity preload",
                "value": "activity",
            }
        },
    ),
    person_ids: list[int] = Query(
        default=[],
        description=(
            "Repeatable person identifiers used to filter contributing "
            "canonical items."
        ),
        openapi_examples={
            "anna": {
                "summary": "Preload only days involving Anna Becker",
                "value": 7,
            }
        },
    ),
    tag_paths: list[str] = Query(
        default=[],
        description=(
            "Repeatable normalized tag paths used to filter contributing "
            "canonical items."
        ),
        openapi_examples={
            "travel_tag": {
                "summary": "Preload only travel-tagged days",
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
                "summary": "Bounding box filter",
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
                "summary": "Radial filter latitude",
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
                "summary": "Radial filter longitude",
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
