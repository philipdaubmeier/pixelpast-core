"""Day-grid exploration projection helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from pixelpast.api.schemas import (
    ExplorationGridDay,
    ExplorationGridResponse,
    ExplorationRange,
)
from pixelpast.persistence.repositories import DailyAggregateReadSnapshot


@dataclass(slots=True, frozen=True)
class ExplorationGridFilters:
    """Server-owned persistent filters for exploration grid requests."""

    view_mode: str
    person_ids: tuple[int, ...] = ()
    tag_paths: tuple[str, ...] = ()
    location_geometry: str | None = None
    distance_latitude: float | None = None
    distance_longitude: float | None = None
    distance_radius_meters: int | None = None
    filename_query: str | None = None


def build_grid_response(
    *,
    start: date,
    end: date,
    aggregate_map: dict[date, DailyAggregateReadSnapshot],
    filters: ExplorationGridFilters,
    days: list[date],
) -> ExplorationGridResponse:
    """Compose a dense exploration grid response for an inclusive date range."""

    return ExplorationGridResponse(
        range=ExplorationRange(start=start, end=end),
        days=[
            build_grid_day_from_aggregate(
                day=current_day,
                aggregate=aggregate_map.get(current_day),
                filters=filters,
            )
            for current_day in days
        ],
    )


def build_grid_day_from_aggregate(
    *,
    day: date,
    aggregate: DailyAggregateReadSnapshot | None,
    filters: ExplorationGridFilters,
) -> ExplorationGridDay:
    """Compose one dense grid day from an overall derived aggregate row."""

    if aggregate is None:
        return empty_grid_day(day)

    person_ids = extract_person_ids_from_summary(aggregate.person_summary_json)
    tag_paths = extract_tag_paths_from_summary(aggregate.tag_summary_json)
    has_data = (
        aggregate.total_events > 0
        or aggregate.media_count > 0
        or aggregate.activity_score > 0
    )
    if not has_data or not matches_grid_filters(
        filters=filters,
        person_ids=person_ids,
        tag_paths=tag_paths,
    ):
        return empty_grid_day(day)

    return ExplorationGridDay(
        date=day,
        activity_score=aggregate.activity_score,
        color_value=get_view_mode_color_value(
            view_mode=filters.view_mode,
            activity_score=aggregate.activity_score,
            person_ids=person_ids,
            tag_paths=tag_paths,
        ),
        has_data=True,
    )


def build_grid_day_from_snapshot(
    *,
    day: date,
    activity_score: int,
    event_count: int,
    asset_count: int,
    person_ids: list[int],
    tag_paths: list[str],
    filters: ExplorationGridFilters,
) -> ExplorationGridDay:
    """Compose one dense grid day from deterministic demo data."""

    has_data = event_count > 0 or asset_count > 0 or activity_score > 0
    if not has_data or not matches_grid_filters(
        filters=filters,
        person_ids=person_ids,
        tag_paths=tag_paths,
    ):
        return empty_grid_day(day)

    return ExplorationGridDay(
        date=day,
        activity_score=activity_score,
        color_value=get_view_mode_color_value(
            view_mode=filters.view_mode,
            activity_score=activity_score,
            person_ids=person_ids,
            tag_paths=tag_paths,
        ),
        has_data=True,
    )


def empty_grid_day(day: date) -> ExplorationGridDay:
    """Return the canonical empty exploration-grid payload."""

    return ExplorationGridDay(
        date=day,
        activity_score=0,
        color_value="empty",
        has_data=False,
    )


def matches_grid_filters(
    *,
    filters: ExplorationGridFilters,
    person_ids: list[int],
    tag_paths: list[str],
) -> bool:
    """Return whether a derived day matches the server-owned persistent filters."""

    if filters.person_ids and not set(person_ids).intersection(filters.person_ids):
        return False

    if filters.tag_paths and not any(
        tag_path_matches_selection(day_tag_path=day_tag_path, selected_tag_path=tag_path)
        for day_tag_path in tag_paths
        for tag_path in filters.tag_paths
    ):
        return False

    return True


def tag_path_matches_selection(
    *,
    day_tag_path: str,
    selected_tag_path: str,
) -> bool:
    """Return whether two normalized tag paths intersect hierarchically."""

    return (
        day_tag_path == selected_tag_path
        or day_tag_path.startswith(f"{selected_tag_path}/")
        or selected_tag_path.startswith(f"{day_tag_path}/")
    )


def get_view_mode_color_value(
    *,
    view_mode: str,
    activity_score: int,
    person_ids: list[int],
    tag_paths: list[str],
) -> str:
    """Resolve the server-side color token for the requested exploration mode."""

    if view_mode == "activity":
        return get_activity_color_value(activity_score)

    if view_mode == "travel":
        if any(tag_path.startswith("travel/") for tag_path in tag_paths):
            return "high"
        if person_ids:
            return "medium"
        return "low" if activity_score >= 55 else "empty"

    if view_mode == "sports":
        if any(tag_path.startswith("activity/") for tag_path in tag_paths):
            return "high"
        if activity_score >= 78:
            return "medium"
        return "low" if activity_score >= 60 else "empty"

    if view_mode == "party_probability":
        if len(person_ids) >= 2:
            return "high"
        if len(person_ids) == 1:
            return "medium"
        return (
            "low"
            if any(tag_path.startswith("people/") for tag_path in tag_paths)
            else "empty"
        )

    return get_activity_color_value(activity_score)


def get_activity_color_value(activity_score: int) -> str:
    """Map an activity score to the shared heatmap intensity token."""

    if activity_score <= 0:
        return "empty"
    if activity_score < 35:
        return "low"
    if activity_score < 70:
        return "medium"
    return "high"


def extract_person_ids_from_summary(
    summaries: list[dict[str, object]],
) -> list[int]:
    """Extract person identifiers from a derived person summary payload."""

    return [summary["person_id"] for summary in summaries if is_person_summary(summary)]


def extract_tag_paths_from_summary(
    summaries: list[dict[str, object]],
) -> list[str]:
    """Extract tag paths from a derived tag summary payload."""

    return [summary["path"] for summary in summaries if is_tag_summary(summary)]


def is_tag_summary(summary: object) -> bool:
    """Return whether an object matches the derived tag summary shape."""

    return (
        isinstance(summary, dict)
        and isinstance(summary.get("path"), str)
        and isinstance(summary.get("label"), str)
        and isinstance(summary.get("count"), int)
    )


def is_person_summary(summary: object) -> bool:
    """Return whether an object matches the derived person summary shape."""

    return (
        isinstance(summary, dict)
        and isinstance(summary.get("person_id"), int)
        and isinstance(summary.get("name"), str)
        and isinstance(summary.get("count"), int)
        and (summary.get("role") is None or isinstance(summary.get("role"), str))
    )
