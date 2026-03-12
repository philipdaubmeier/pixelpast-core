"""Timeline-oriented API endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from pixelpast.api.dependencies import get_db_session
from pixelpast.api.schemas import DayDetailResponse, HeatmapResponse
from pixelpast.api.services import TimelineQueryService
from pixelpast.persistence.repositories import (
    DailyAggregateReadRepository,
    DayTimelineRepository,
)

router = APIRouter(tags=["timeline"])


def get_timeline_query_service(
    session: Session = Depends(get_db_session),
) -> TimelineQueryService:
    """Build the read service for timeline endpoints."""

    return TimelineQueryService(
        daily_aggregate_repository=DailyAggregateReadRepository(session),
        day_timeline_repository=DayTimelineRepository(session),
    )


@router.get("/heatmap", response_model=HeatmapResponse)
def get_heatmap(
    start: date = Query(...),
    end: date = Query(...),
    service: TimelineQueryService = Depends(get_timeline_query_service),
) -> HeatmapResponse:
    """Return derived day-level activity data for a UTC date range."""

    if start > end:
        raise HTTPException(
            status_code=400,
            detail="start must be less than or equal to end",
        )

    return service.get_heatmap(start=start, end=end)


@router.get("/days/{day}", response_model=DayDetailResponse)
def get_day_detail(
    day: date,
    service: TimelineQueryService = Depends(get_timeline_query_service),
) -> DayDetailResponse:
    """Return a unified event and asset view for one UTC day."""

    return service.get_day_detail(day=day)
