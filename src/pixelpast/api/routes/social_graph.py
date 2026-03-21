"""Routes for social-graph projection reads."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from pixelpast.api.providers import SocialGraphProjectionProvider
from pixelpast.api.routes.metadata import (
    BAD_REQUEST_RESPONSE,
    VALIDATION_ERROR_RESPONSE,
    combine_responses,
)
from pixelpast.api.routes.shared import (
    build_social_graph_filters,
    get_social_graph_projection_provider,
    validate_optional_range,
)
from pixelpast.api.schemas import SocialGraphResponse

router = APIRouter(tags=["social"])


@router.get(
    "/social/graph",
    response_model=SocialGraphResponse,
    summary="Get social graph projection",
    description=(
        "Return a person co-occurrence graph derived from qualifying assets "
        "within the resolved inclusive UTC date range."
    ),
    response_description=(
        "Person nodes and weighted links for the filtered social graph."
    ),
    responses=combine_responses(BAD_REQUEST_RESPONSE, VALIDATION_ERROR_RESPONSE),
)
def get_social_graph(
    start: date | None = Query(
        default=None,
        description=(
            "Inclusive UTC start date for the requested social-graph window. "
            "Must be provided together with end."
        ),
    ),
    end: date | None = Query(
        default=None,
        description=(
            "Inclusive UTC end date for the requested social-graph window. "
            "Must be provided together with start."
        ),
    ),
    person_ids: list[int] = Query(
        default=[],
        description=(
            "Repeatable seed person identifiers. Only assets containing at "
            "least one selected person qualify when this filter is present."
        ),
    ),
    max_people_per_asset: int = Query(
        default=10,
        ge=2,
        le=30,
        description=(
            "Ignore assets that contain more than this many linked people to "
            "avoid oversized group shots dominating the graph."
        ),
    ),
    tag_paths: list[str] = Query(
        default=[],
        description=(
            "Reserved filter parameter. The current social graph contract "
            "rejects tag-based filtering."
        ),
    ),
    location_geometry: str | None = Query(
        default=None,
        description=(
            "Reserved filter parameter. The current social graph contract "
            "rejects geometry-based filtering."
        ),
    ),
    distance_latitude: float | None = Query(
        default=None,
        ge=-90,
        le=90,
        description=(
            "Reserved filter parameter. The current social graph contract "
            "rejects radial distance filtering."
        ),
    ),
    distance_longitude: float | None = Query(
        default=None,
        ge=-180,
        le=180,
        description=(
            "Reserved filter parameter. The current social graph contract "
            "rejects radial distance filtering."
        ),
    ),
    distance_radius_meters: int | None = Query(
        default=None,
        ge=1,
        description=(
            "Reserved filter parameter. The current social graph contract "
            "rejects radial distance filtering."
        ),
    ),
    filename_query: str | None = Query(
        default=None,
        min_length=1,
        description=(
            "Reserved filter parameter. The current social graph contract "
            "rejects filename-based filtering."
        ),
    ),
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
