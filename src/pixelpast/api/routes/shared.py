"""Shared dependencies and validators for timeline-oriented routes."""

from __future__ import annotations

from collections.abc import Generator
from datetime import date

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session, sessionmaker

from pixelpast.api.dependencies import get_app_settings, get_db_session
from pixelpast.api.providers import (
    DatabaseTimelineProjectionProvider,
    DemoTimelineProjectionProvider,
    ExplorationGridFilters,
    TimelineProjectionProvider,
    get_default_view_modes,
)
from pixelpast.api.services import TimelineQueryService
from pixelpast.persistence.repositories import (
    DailyAggregateReadRepository,
    DayTimelineRepository,
    ExplorationReadRepository,
)
from pixelpast.shared.settings import Settings


def get_timeline_query_service(
    session: Session = Depends(get_db_session),
) -> TimelineQueryService:
    """Build the read service for timeline detail endpoints."""

    return TimelineQueryService(
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


def validate_optional_range(*, start: date | None, end: date | None) -> None:
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


def build_exploration_grid_filters(
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
