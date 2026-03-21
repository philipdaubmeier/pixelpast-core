"""Routes for exploration bootstrap UI data."""

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
    get_timeline_projection_provider,
    validate_optional_range,
)
from pixelpast.api.schemas import ExplorationBootstrapResponse

router = APIRouter(tags=["timeline"])


@router.get(
    "/exploration/bootstrap",
    response_model=ExplorationBootstrapResponse,
    summary="Get exploration bootstrap metadata",
    description=(
        "Return exploration shell metadata for the resolved date range, "
        "including available view modes, known people, and tags, without the "
        "dense day grid payload."
    ),
    response_description=(
        "Exploration shell metadata for the resolved inclusive UTC date range."
    ),
    responses=combine_responses(BAD_REQUEST_RESPONSE, VALIDATION_ERROR_RESPONSE),
)
def get_exploration_bootstrap(
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
    provider: TimelineProjectionProvider = Depends(get_timeline_projection_provider),
) -> ExplorationBootstrapResponse:
    """Return exploration shell metadata without dense grid payloads."""

    validate_optional_range(start=start, end=end)
    return provider.get_exploration_bootstrap(
        start=start,
        end=end,
        today=date.today(),
    )
