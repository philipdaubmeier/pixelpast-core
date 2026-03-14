"""Routes for hover-context timeline data."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from pixelpast.api.dependencies import get_app_settings
from pixelpast.api.providers import TimelineProjectionProvider
from pixelpast.api.routes.shared import get_timeline_projection_provider
from pixelpast.api.schemas import DayContextResponse
from pixelpast.shared.settings import Settings

router = APIRouter(tags=["timeline"])


@router.get("/days/context", response_model=DayContextResponse)
def get_day_context(
    start: date = Query(...),
    end: date = Query(...),
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

    return provider.get_day_context(start=start, end=end)
