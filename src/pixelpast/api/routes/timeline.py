"""Timeline-oriented API endpoints."""

from __future__ import annotations

from collections.abc import Generator
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, sessionmaker

from pixelpast.api.dependencies import get_app_settings, get_db_session
from pixelpast.api.providers import (
    DatabaseTimelineProjectionProvider,
    DemoTimelineProjectionProvider,
    ExplorationGridFilters,
    TimelineProjectionProvider,
    get_default_view_modes,
)
from pixelpast.api.schemas import (
    DayContextResponse,
    DayDetailResponse,
    ExplorationBootstrapResponse,
    ExplorationGridResponse,
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
    )


def get_timeline_projection_provider(
    request: Request,
    settings: Settings = Depends(get_app_settings),
) -> Generator[TimelineProjectionProvider, None, None]:
    """Build the projection provider selected for exploration endpoints."""

    if settings.timeline_projection_provider == "demo":
        yield DemoTimelineProjectionProvider()
        return

    session_factory: sessionmaker[Session] = request.app.state.session_factory
    session = session_factory()
    try:
        yield DatabaseTimelineProjectionProvider(
            daily_aggregate_repository=DailyAggregateReadRepository(session),
            exploration_repository=ExplorationReadRepository(session),
        )
    finally:
        session.close()


def _validate_optional_range(*, start: date | None, end: date | None) -> None:
    """Validate the optional exploration range query."""

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


def _build_exploration_grid_filters(
    *,
    view_mode: str,
    person_ids: list[int],
    tag_paths: list[str],
    location_geometry: str | None,
    distance_latitude: float | None,
    distance_longitude: float | None,
    distance_radius_meters: int | None,
    filename_query: str | None,
) -> ExplorationGridFilters:
    """Normalize server-side persistent filter inputs for grid requests."""

    valid_view_modes = {mode.id for mode in get_default_view_modes()}
    if view_mode not in valid_view_modes:
        raise HTTPException(
            status_code=400,
            detail=f"unsupported view_mode: {view_mode}",
        )

    return ExplorationGridFilters(
        view_mode=view_mode,
        person_ids=tuple(sorted(set(person_ids))),
        tag_paths=tuple(sorted(set(tag_paths))),
        location_geometry=location_geometry,
        distance_latitude=distance_latitude,
        distance_longitude=distance_longitude,
        distance_radius_meters=distance_radius_meters,
        filename_query=filename_query,
    )


@router.get("/exploration/bootstrap", response_model=ExplorationBootstrapResponse)
def get_exploration_bootstrap(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    provider: TimelineProjectionProvider = Depends(get_timeline_projection_provider),
) -> ExplorationBootstrapResponse:
    """Return exploration shell metadata without dense grid payloads."""

    _validate_optional_range(start=start, end=end)
    return provider.get_exploration_bootstrap(
        start=start,
        end=end,
        today=date.today(),
    )


@router.get("/exploration", response_model=ExplorationGridResponse)
def get_exploration(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    view_mode: str = Query(default="activity"),
    person_ids: list[int] = Query(default=[]),
    tag_paths: list[str] = Query(default=[]),
    location_geometry: str | None = Query(default=None),
    distance_latitude: float | None = Query(default=None),
    distance_longitude: float | None = Query(default=None),
    distance_radius_meters: int | None = Query(default=None, ge=1),
    filename_query: str | None = Query(default=None),
    provider: TimelineProjectionProvider = Depends(get_timeline_projection_provider),
) -> ExplorationGridResponse:
    """Return derived-only dense grid activity with server-owned filters."""

    _validate_optional_range(start=start, end=end)
    filters = _build_exploration_grid_filters(
        view_mode=view_mode,
        person_ids=person_ids,
        tag_paths=tag_paths,
        location_geometry=location_geometry,
        distance_latitude=distance_latitude,
        distance_longitude=distance_longitude,
        distance_radius_meters=distance_radius_meters,
        filename_query=filename_query,
    )
    return provider.get_exploration_grid(
        start=start,
        end=end,
        today=date.today(),
        filters=filters,
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


@router.get("/days/{day}", response_model=DayDetailResponse)
def get_day_detail(
    day: date,
    service: TimelineQueryService = Depends(get_timeline_query_service),
) -> DayDetailResponse:
    """Return a unified event and asset view for one UTC day."""

    return service.get_day_detail(day=day)
