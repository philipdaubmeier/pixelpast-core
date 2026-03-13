"""Timeline-oriented API endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from pixelpast.api.dependencies import get_app_settings, get_db_session
from pixelpast.api.schemas import (
    DayContextResponse,
    DayDetailResponse,
    ExplorationResponse,
    HeatmapResponse,
)
from pixelpast.api.services import TimelineQueryService
from pixelpast.persistence.repositories import (
    DailyAggregateReadRepository,
    DayTimelineRepository,
    ExplorationReadRepository,
)
from pixelpast.shared.settings import Settings

router = APIRouter(tags=["timeline"])


def get_timeline_query_service(
    session: Session = Depends(get_db_session),
) -> TimelineQueryService:
    """Build the read service for timeline endpoints."""

    return TimelineQueryService(
        daily_aggregate_repository=DailyAggregateReadRepository(session),
        day_timeline_repository=DayTimelineRepository(session),
        exploration_repository=ExplorationReadRepository(session),
    )


@router.get("/exploration", response_model=ExplorationResponse)
def get_exploration(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    service: TimelineQueryService = Depends(get_timeline_query_service),
) -> ExplorationResponse:
    """Return a dense exploration bootstrap projection for the UI shell."""

    if (start is None) != (end is None):
        raise HTTPException(
            status_code=400,
            detail="start and end must both be provided together",
        )
    if start is not None and end is not None and start > end:
        raise HTTPException(
            status_code=400,
            detail="start must be less than or equal to end",
        )

    return service.get_exploration(start=start, end=end, today=date.today())


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


@router.get("/days/context", response_model=DayContextResponse)
def get_day_context(
    start: date = Query(...),
    end: date = Query(...),
    settings: Settings = Depends(get_app_settings),
    service: TimelineQueryService = Depends(get_timeline_query_service),
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

    return service.get_day_context(start=start, end=end)


@router.get("/days/{day}", response_model=DayDetailResponse)
def get_day_detail(
    day: date,
    service: TimelineQueryService = Depends(get_timeline_query_service),
) -> DayDetailResponse:
    """Return a unified event and asset view for one UTC day."""

    return service.get_day_detail(day=day)
