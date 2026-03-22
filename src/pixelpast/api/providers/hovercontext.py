"""Hover-context projection helpers."""

from __future__ import annotations

from datetime import date

from pixelpast.api.providers.daygrid import (
    ExplorationGridFilters,
    extract_person_ids_from_summary,
    extract_tag_paths_from_summary,
    matches_grid_filters,
)
from pixelpast.api.schemas import (
    DayContextDay,
    DayContextMapPoint,
    DayContextResponse,
    DayContextSummaryCounts,
    ExplorationPerson,
    ExplorationRange,
    ExplorationTag,
)
from pixelpast.persistence.repositories import DailyAggregateReadSnapshot


def build_day_context_response(
    *,
    start: date,
    end: date,
    aggregates_by_day: dict[date, DailyAggregateReadSnapshot],
    filters: ExplorationGridFilters,
    days: list[date],
) -> DayContextResponse:
    """Compose the hover-context payload for an inclusive date range."""

    return DayContextResponse(
        range=ExplorationRange(start=start, end=end),
        days=[
            build_day_context_day(
                day=current_day,
                aggregate=aggregates_by_day.get(current_day),
                filters=filters,
            )
            for current_day in days
        ],
    )


def build_day_context_day(
    *,
    day: date,
    aggregate: DailyAggregateReadSnapshot | None,
    filters: ExplorationGridFilters,
) -> DayContextDay:
    """Return one hover-context day constrained to the active derived view."""

    if aggregate is None:
        return empty_day_context(day)

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
        return empty_day_context(day)

    map_points = build_day_context_map_points(
        day=day,
        summaries=aggregate.location_summary_json,
    )
    return DayContextDay(
        date=day,
        persons=build_day_context_persons(aggregate.person_summary_json),
        tags=build_day_context_tags(aggregate.tag_summary_json),
        map_points=map_points,
        summary_counts=DayContextSummaryCounts(
            events=aggregate.total_events,
            assets=aggregate.media_count,
            places=len(map_points),
        ),
    )


def empty_day_context(day: date) -> DayContextDay:
    """Return the canonical empty hover-context payload."""

    return DayContextDay(
        date=day,
        persons=[],
        tags=[],
        map_points=[],
        summary_counts=DayContextSummaryCounts(events=0, assets=0, places=0),
    )


def build_day_context_persons(
    summaries: list[dict[str, object]],
) -> list[ExplorationPerson]:
    """Build sorted person payloads from one derived aggregate summary."""

    persons: dict[int, ExplorationPerson] = {}
    for summary in summaries:
        person_id = summary.get("person_id")
        name = summary.get("name")
        role = summary.get("role")
        if not isinstance(person_id, int) or not isinstance(name, str):
            continue
        if role is not None and not isinstance(role, str):
            continue
        persons.setdefault(
            person_id,
            ExplorationPerson(
                id=person_id,
                name=name,
                role=role,
            ),
        )

    return sorted(persons.values(), key=lambda person: (person.name.casefold(), person.id))


def build_day_context_tags(
    summaries: list[dict[str, object]],
) -> list[ExplorationTag]:
    """Build sorted tag payloads from one derived aggregate summary."""

    tags: dict[str, ExplorationTag] = {}
    for summary in summaries:
        path = summary.get("path")
        label = summary.get("label")
        if not isinstance(path, str) or not isinstance(label, str):
            continue
        tags.setdefault(
            path,
            ExplorationTag(path=path, label=label),
        )

    return sorted(tags.values(), key=lambda tag: (tag.path, tag.label.casefold()))


def build_day_context_map_points(
    *,
    day: date,
    summaries: list[dict[str, object]],
) -> list[DayContextMapPoint]:
    """Build sorted map points from one derived aggregate location summary."""

    points: list[DayContextMapPoint] = []
    for index, summary in enumerate(summaries, start=1):
        label = summary.get("label")
        latitude = summary.get("latitude")
        longitude = summary.get("longitude")
        if not isinstance(latitude, (int, float)) or not isinstance(
            longitude, (int, float)
        ):
            continue
        normalized_label = (
            label.strip() if isinstance(label, str) and label.strip() else None
        )
        points.append(
            DayContextMapPoint(
                id=(
                    f"location:{day.isoformat()}:{index}"
                    if normalized_label is not None
                    else None
                ),
                label=normalized_label,
                latitude=float(latitude),
                longitude=float(longitude),
            )
        )

    return points
