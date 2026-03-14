"""Routes for exploration bootstrap UI data."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from pixelpast.api.providers import TimelineProjectionProvider
from pixelpast.api.routes.shared import (
    get_timeline_projection_provider,
    validate_optional_range,
)
from pixelpast.api.schemas import ExplorationBootstrapResponse

router = APIRouter(tags=["timeline"])


@router.get("/exploration/bootstrap", response_model=ExplorationBootstrapResponse)
def get_exploration_bootstrap(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    provider: TimelineProjectionProvider = Depends(get_timeline_projection_provider),
) -> ExplorationBootstrapResponse:
    """Return exploration shell metadata without dense grid payloads."""

    validate_optional_range(start=start, end=end)
    return provider.get_exploration_bootstrap(
        start=start,
        end=end,
        today=date.today(),
    )
