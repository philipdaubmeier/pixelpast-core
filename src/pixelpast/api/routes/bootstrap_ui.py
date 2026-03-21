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

BOOTSTRAP_SUCCESS_EXAMPLES = {
    "winter_overview": {
        "summary": "Bootstrap metadata for a winter exploration window",
        "value": {
            "range": {"start": "2026-01-01", "end": "2026-01-31"},
            "view_modes": [
                {
                    "id": "activity",
                    "label": "Activity",
                    "description": "Overall day activity score across all imported sources.",
                },
                {
                    "id": "workdays_vacation",
                    "label": "Vacation",
                    "description": "Workday and vacation classification for each calendar day.",
                },
            ],
            "persons": [
                {"id": 7, "name": "Anna Becker", "role": "family"},
                {"id": 12, "name": "Milo Tan", "role": "friend"},
            ],
            "tags": [
                {"path": "travel/italy/venice", "label": "Venice"},
                {"path": "music/concert/live", "label": "Live Concert"},
            ],
        },
    }
}


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
    responses=combine_responses(
        {
            200: {
                "content": {
                    "application/json": {
                        "examples": BOOTSTRAP_SUCCESS_EXAMPLES,
                    }
                }
            }
        },
        BAD_REQUEST_RESPONSE,
        VALIDATION_ERROR_RESPONSE,
    ),
)
def get_exploration_bootstrap(
    start: date | None = Query(
        default=None,
        description=(
            "Inclusive UTC start date for the requested exploration window. "
            "Must be provided together with end."
        ),
        openapi_examples={
            "winter_window": {
                "summary": "Window start for January 2026",
                "value": "2026-01-01",
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
            "winter_window": {
                "summary": "Window end for January 2026",
                "value": "2026-01-31",
            }
        },
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
