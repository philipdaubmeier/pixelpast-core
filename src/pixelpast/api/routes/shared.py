"""Shared dependencies and validators for timeline-oriented routes."""

from __future__ import annotations

from collections.abc import Generator
from datetime import date

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session, sessionmaker

from pixelpast.api.dependencies import get_app_settings, get_db_session
from pixelpast.api.providers import (
    DatabaseSocialGraphProjectionProvider,
    DatabaseTimelineProjectionProvider,
    DemoSocialGraphProjectionProvider,
    DemoTimelineProjectionProvider,
    ExplorationGridFilters,
    SocialGraphFilters,
    SocialGraphProjectionProvider,
    TimelineProjectionProvider,
)
from pixelpast.api.services import TimelineQueryService
from pixelpast.persistence.repositories import (
    DailyAggregateReadRepository,
    DayTimelineRepository,
    ExplorationReadRepository,
    SocialGraphReadRepository,
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


def get_social_graph_projection_provider(
    request: Request,
    settings: Settings = Depends(get_app_settings),
) -> Generator[SocialGraphProjectionProvider, None, None]:
    """Build the projection provider selected for social-graph endpoints."""

    if settings.timeline_projection_provider == "demo":
        yield DemoSocialGraphProjectionProvider()
        return

    session_factory: sessionmaker[Session] = request.app.state.session_factory
    session = session_factory()
    try:
        yield DatabaseSocialGraphProjectionProvider(
            social_graph_repository=SocialGraphReadRepository(session),
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
    provider: TimelineProjectionProvider,
    person_ids: list[int],
    tag_paths: list[str],
    location_geometry: str | None,
    distance_latitude: float | None,
    distance_longitude: float | None,
    distance_radius_meters: int | None,
    filename_query: str | None,
) -> ExplorationGridFilters:
    """Normalize server-side persistent filter inputs for grid requests."""

    valid_view_modes = set(provider.list_available_view_modes())
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


def build_social_graph_filters(
    *,
    person_ids: list[int],
    max_people_per_asset: int,
    tag_paths: list[str],
    location_geometry: str | None,
    distance_latitude: float | None,
    distance_longitude: float | None,
    distance_radius_meters: int | None,
    filename_query: str | None,
) -> SocialGraphFilters:
    """Normalize supported filters and reject unsupported social-graph filters."""

    unsupported_filters: list[str] = []
    if tag_paths:
        unsupported_filters.append("tag_paths")
    if location_geometry is not None:
        unsupported_filters.append("location_geometry")
    if distance_latitude is not None:
        unsupported_filters.append("distance_latitude")
    if distance_longitude is not None:
        unsupported_filters.append("distance_longitude")
    if distance_radius_meters is not None:
        unsupported_filters.append("distance_radius_meters")
    if filename_query is not None:
        unsupported_filters.append("filename_query")

    if unsupported_filters:
        raise HTTPException(
            status_code=400,
            detail=(
                "unsupported social graph filters: "
                + ", ".join(sorted(unsupported_filters))
                + "; supported filters: start, end, person_ids, max_people_per_asset"
            ),
        )

    return SocialGraphFilters(
        person_ids=tuple(sorted(set(person_ids))),
        max_people_per_asset=max_people_per_asset,
    )
