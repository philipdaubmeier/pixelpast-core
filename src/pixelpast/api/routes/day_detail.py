"""Routes for single-day timeline detail reads."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends

from pixelpast.api.routes.shared import get_timeline_query_service
from pixelpast.api.schemas import DayDetailResponse
from pixelpast.api.services import TimelineQueryService

router = APIRouter(tags=["timeline"])


@router.get("/days/{day}", response_model=DayDetailResponse)
def get_day_detail(
    day: date,
    service: TimelineQueryService = Depends(get_timeline_query_service),
) -> DayDetailResponse:
    """Return a unified event and asset view for one UTC day."""

    return service.get_day_detail(day=day)
