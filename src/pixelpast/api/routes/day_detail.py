"""Routes for single-day timeline detail reads."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Path

from pixelpast.api.routes.metadata import VALIDATION_ERROR_RESPONSE
from pixelpast.api.routes.shared import get_timeline_query_service
from pixelpast.api.schemas import DayDetailResponse
from pixelpast.api.services import TimelineQueryService

router = APIRouter(tags=["timeline"])


@router.get(
    "/days/{day}",
    response_model=DayDetailResponse,
    summary="Get one day timeline",
    description=(
        "Return the unified canonical event and asset timeline for a single "
        "UTC calendar day, ordered by timestamp."
    ),
    response_description="Chronological event and asset items for one UTC day.",
    responses=VALIDATION_ERROR_RESPONSE,
)
def get_day_detail(
    day: date = Path(
        ...,
        description="UTC calendar day to inspect in ISO format (YYYY-MM-DD).",
    ),
    service: TimelineQueryService = Depends(get_timeline_query_service),
) -> DayDetailResponse:
    """Return a unified event and asset view for one UTC day."""

    return service.get_day_detail(day=day)
