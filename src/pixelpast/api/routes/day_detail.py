"""Routes for single-day timeline detail reads."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Path

from pixelpast.api.routes.metadata import VALIDATION_ERROR_RESPONSE
from pixelpast.api.routes.shared import get_timeline_query_service
from pixelpast.api.schemas import DayDetailResponse
from pixelpast.api.services import TimelineQueryService

router = APIRouter(tags=["timeline"])

DAY_DETAIL_SUCCESS_EXAMPLES = {
    "mixed_day_timeline": {
        "summary": "Chronological event and asset timeline for one day",
        "value": {
            "date": "2026-07-14",
            "items": [
                {
                    "item_type": "event",
                    "id": 1042,
                    "timestamp": "2026-07-14T08:30:00Z",
                    "event_type": "calendar",
                    "title": "Flight to Lisbon",
                    "summary": "TXL to LIS with morning check-in",
                },
                {
                    "item_type": "asset",
                    "id": 8801,
                    "timestamp": "2026-07-14T14:12:43Z",
                    "media_type": "image",
                    "external_id": "photos/2026/07/IMG_1042.JPG",
                },
                {
                    "item_type": "event",
                    "id": 1043,
                    "timestamp": "2026-07-14T19:00:00Z",
                    "event_type": "music_play",
                    "title": "Fado Playlist",
                    "summary": "Spotify playback during evening walk",
                },
            ],
        },
    }
}


@router.get(
    "/days/{day}",
    response_model=DayDetailResponse,
    summary="Get one day timeline",
    description=(
        "Return the unified canonical event and asset timeline for a single "
        "UTC calendar day, ordered by timestamp."
    ),
    response_description="Chronological event and asset items for one UTC day.",
    responses={
        200: {
            "content": {
                "application/json": {
                    "examples": DAY_DETAIL_SUCCESS_EXAMPLES,
                }
            }
        },
        **VALIDATION_ERROR_RESPONSE,
    },
)
def get_day_detail(
    day: date = Path(
        ...,
        description="UTC calendar day to inspect in ISO format (YYYY-MM-DD).",
        openapi_examples={
            "summer_day": {
                "summary": "One summer travel day",
                "value": "2026-07-14",
            }
        },
    ),
    service: TimelineQueryService = Depends(get_timeline_query_service),
) -> DayDetailResponse:
    """Return a unified event and asset view for one UTC day."""

    return service.get_day_detail(day=day)
