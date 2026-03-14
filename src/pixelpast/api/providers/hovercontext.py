"""Hover-context projection helpers."""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from pixelpast.api.schemas import (
    DayContextDay,
    DayContextMapPoint,
    DayContextResponse,
    DayContextSummaryCounts,
    ExplorationPerson,
    ExplorationRange,
    ExplorationTag,
)
from pixelpast.persistence.repositories import (
    DayActivityItemSnapshot,
    DayMapPointSnapshot,
    DayPersonLinkSnapshot,
    DayTagLinkSnapshot,
)


def build_day_context_response(
    *,
    start: date,
    end: date,
    event_days: list[DayActivityItemSnapshot],
    asset_days: list[DayActivityItemSnapshot],
    person_links: list[DayPersonLinkSnapshot],
    tag_links: list[DayTagLinkSnapshot],
    map_points: list[DayMapPointSnapshot],
    days: list[date],
) -> DayContextResponse:
    """Compose the hover-context payload for an inclusive date range."""

    event_counts = count_items_by_day(event_days)
    asset_counts = count_items_by_day(asset_days)
    persons_by_day = build_day_context_persons(person_links)
    tags_by_day = build_day_context_tags(tag_links)
    map_points_by_day = build_day_context_map_points(map_points)

    return DayContextResponse(
        range=ExplorationRange(start=start, end=end),
        days=[
            DayContextDay(
                date=current_day,
                persons=persons_by_day.get(current_day, []),
                tags=tags_by_day.get(current_day, []),
                map_points=map_points_by_day.get(current_day, []),
                summary_counts=DayContextSummaryCounts(
                    events=event_counts.get(current_day, 0),
                    assets=asset_counts.get(current_day, 0),
                    places=len(map_points_by_day.get(current_day, [])),
                ),
            )
            for current_day in days
        ],
    )


def count_items_by_day(snapshots: list[DayActivityItemSnapshot]) -> dict[date, int]:
    """Count canonical timeline items per UTC day."""

    counts: dict[date, int] = defaultdict(int)
    for snapshot in snapshots:
        counts[snapshot.day] += 1
    return dict(counts)


def build_day_context_persons(
    links: list[DayPersonLinkSnapshot],
) -> dict[date, list[ExplorationPerson]]:
    """Build sorted per-day person payloads for hover context."""

    persons_by_day: dict[date, dict[int, ExplorationPerson]] = defaultdict(dict)

    for link in links:
        persons_by_day[link.day].setdefault(
            link.person_id,
            ExplorationPerson(
                id=link.person_id,
                name=link.person_name,
                role=link.person_role,
            ),
        )

    return {
        day: sorted(
            persons.values(),
            key=lambda person: (person.name.casefold(), person.id),
        )
        for day, persons in persons_by_day.items()
    }


def build_day_context_tags(
    links: list[DayTagLinkSnapshot],
) -> dict[date, list[ExplorationTag]]:
    """Build sorted per-day tag payloads for hover context."""

    tags_by_day: dict[date, dict[str, ExplorationTag]] = defaultdict(dict)

    for link in links:
        tags_by_day[link.day].setdefault(
            link.tag_path,
            ExplorationTag(path=link.tag_path, label=link.tag_label),
        )

    return {
        day: sorted(
            tags.values(),
            key=lambda tag: (tag.path, tag.label.casefold()),
        )
        for day, tags in tags_by_day.items()
    }


def build_day_context_map_points(
    snapshots: list[DayMapPointSnapshot],
) -> dict[date, list[DayContextMapPoint]]:
    """Build sorted per-day map points for hover context."""

    points_by_day: dict[date, list[DayContextMapPoint]] = defaultdict(list)

    for snapshot in snapshots:
        points_by_day[snapshot.day].append(
            DayContextMapPoint(
                id=f"{snapshot.item_type}:{snapshot.item_id}",
                label=resolve_map_point_label(snapshot),
                latitude=snapshot.latitude,
                longitude=snapshot.longitude,
            )
        )

    return dict(points_by_day)


def resolve_map_point_label(snapshot: DayMapPointSnapshot) -> str:
    """Return a stable display label for a coordinate-bearing canonical item."""

    if snapshot.label is not None:
        normalized = snapshot.label.strip()
        if normalized:
            return normalized

    if snapshot.fallback_identifier is not None:
        normalized_identifier = snapshot.fallback_identifier.strip()
        if normalized_identifier:
            return normalized_identifier

    return f"{humanize_label(snapshot.fallback_type)} #{snapshot.item_id}"


def humanize_label(value: str) -> str:
    """Convert a canonical type token into a lightweight display label."""

    parts = [part for part in value.replace("-", "_").split("_") if part]
    if not parts:
        return "Item"
    return " ".join(part.capitalize() for part in parts)
