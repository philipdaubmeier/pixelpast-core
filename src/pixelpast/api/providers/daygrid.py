"""Day-grid exploration projection helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from pixelpast.api.schemas import (
    ExplorationGridDay,
    ExplorationGridResponse,
    ExplorationRange,
)
from pixelpast.analytics.daily_views import build_default_daily_view_metadata
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


def has_item_level_filters(*, filters: ExplorationGridFilters) -> bool:
    """Return whether persistent filters require canonical item-level evaluation."""

    return bool(filters.person_ids or filters.tag_paths)


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

    color = resolve_grid_day_color(aggregate=aggregate)
    return ExplorationGridDay(
        date=day,
        count=aggregate.total_events + aggregate.media_count,
        color=color,
        label=aggregate.title,
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
        count=event_count + asset_count,
        color=get_view_mode_color_value(
            activity_score=activity_score,
            metadata_json=build_default_daily_view_metadata(),
        ),
    )


def empty_grid_day(day: date) -> ExplorationGridDay:
    """Return the canonical empty exploration-grid payload."""

    return ExplorationGridDay(
        date=day,
        count=0,
        color="empty",
    )


def resolve_grid_day_color(*, aggregate: DailyAggregateReadSnapshot) -> str:
    """Resolve either direct per-day color output or token-based color output."""

    if uses_direct_color(metadata_json=aggregate.metadata_json):
        direct_color = aggregate.color_value
        if isinstance(direct_color, str) and direct_color.startswith("#"):
            return direct_color
        return "empty"

    return get_view_mode_color_value(
        activity_score=aggregate.activity_score,
        metadata_json=aggregate.metadata_json,
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
    activity_score: int,
    metadata_json: dict[str, Any],
) -> str:
    """Resolve the server-side color token from daily-view metadata thresholds."""

    thresholds = parse_activity_score_color_thresholds(metadata_json=metadata_json)
    if thresholds is None:
        thresholds = parse_activity_score_color_thresholds(
            metadata_json=build_default_daily_view_metadata()
        )
        assert thresholds is not None

    return resolve_color_value_from_thresholds(
        activity_score=activity_score,
        thresholds=thresholds,
    )


def uses_direct_color(*, metadata_json: dict[str, Any]) -> bool:
    """Return whether the selected daily view expects direct hex day colors."""

    return metadata_json.get("direct_color") is True


def parse_activity_score_color_thresholds(
    *,
    metadata_json: dict[str, Any],
) -> list[tuple[int, str]] | None:
    """Return validated activity-score thresholds from daily-view metadata."""

    raw_thresholds = metadata_json.get("activity_score_color_thresholds")
    if not isinstance(raw_thresholds, list):
        return None

    thresholds: list[tuple[int, str]] = []
    for entry in raw_thresholds:
        if not is_activity_score_color_threshold(entry):
            return None
        thresholds.append((entry["activity_score"], entry["color_value"]))

    return sorted(thresholds, key=lambda threshold: (threshold[0], threshold[1]))


def resolve_color_value_from_thresholds(
    *,
    activity_score: int,
    thresholds: list[tuple[int, str]],
) -> str:
    """Map one activity score to the highest matching configured color value."""

    matching_color = "empty"
    for threshold_score, color_value in thresholds:
        if activity_score >= threshold_score:
            matching_color = color_value

    return matching_color


def is_activity_score_color_threshold(entry: object) -> bool:
    """Return whether one metadata entry matches the threshold mapping shape."""

    return (
        isinstance(entry, dict)
        and isinstance(entry.get("activity_score"), int)
        and isinstance(entry.get("color_value"), str)
        and entry["color_value"] in {"empty", "low", "medium", "high"}
    )


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
