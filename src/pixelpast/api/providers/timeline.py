"""Projection providers for exploration-oriented API responses."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Final, Protocol

from pixelpast.api.schemas import (
    DayContextDay,
    DayContextMapPoint,
    DayContextResponse,
    DayContextSummaryCounts,
    ExplorationDay,
    ExplorationDayDerivedSummary,
    ExplorationDayLocationSummary,
    ExplorationDayPersonSummary,
    ExplorationDaySourceSummary,
    ExplorationDayTagSummary,
    ExplorationPerson,
    ExplorationRange,
    ExplorationResponse,
    ExplorationTag,
    ExplorationViewMode,
)
from pixelpast.persistence.repositories import (
    DailyAggregateReadRepository,
    DailyAggregateReadSnapshot,
    DayActivityItemSnapshot,
    DayMapPointSnapshot,
    DayPersonLinkSnapshot,
    DayTagLinkSnapshot,
    ExplorationReadRepository,
)

_VIEW_MODE_DEFINITIONS: Final[tuple[tuple[str, str, str], ...]] = (
    (
        "activity",
        "Activity",
        "Default heat intensity across all timeline sources.",
    ),
    (
        "travel",
        "Travel",
        "Highlights movement-heavy and location-rich days.",
    ),
    (
        "sports",
        "Sports",
        "Reserves the grid for workout and fitness projections.",
    ),
    (
        "party_probability",
        "Social",
        "Placeholder derived view for future social-density signals.",
    ),
)

_DEMO_DEFAULT_RANGE: Final[tuple[date, date]] = (
    date(2021, 1, 1),
    date(2026, 12, 31),
)
_DEMO_REFERENCE_DATE: Final[date] = date(2021, 1, 1)


@dataclass(slots=True, frozen=True)
class _DemoPersonDefinition:
    id: int
    name: str
    role: str | None


@dataclass(slots=True, frozen=True)
class _DemoTagDefinition:
    path: str
    label: str


@dataclass(slots=True, frozen=True)
class _DemoLocationDefinition:
    slug: str
    label: str
    latitude: float
    longitude: float


@dataclass(slots=True, frozen=True)
class _DemoDaySnapshot:
    event_count: int
    asset_count: int
    activity_score: int
    person_ids: tuple[int, ...]
    tag_paths: tuple[str, ...]
    map_points: tuple[DayContextMapPoint, ...]


class TimelineProjectionProvider(Protocol):
    """Provide API-ready exploration and hover projections."""

    def get_day_context(self, *, start: date, end: date) -> DayContextResponse:
        """Return dense hover-context data for an inclusive date range."""
        ...

    def get_exploration(
        self,
        *,
        start: date | None,
        end: date | None,
        today: date,
    ) -> ExplorationResponse:
        """Return dense exploration bootstrap data for the resolved date window."""
        ...


class DatabaseTimelineProjectionProvider:
    """Build exploration projections from canonical and derived repositories."""

    def __init__(
        self,
        *,
        daily_aggregate_repository: DailyAggregateReadRepository,
        exploration_repository: ExplorationReadRepository,
    ) -> None:
        self._daily_aggregate_repository = daily_aggregate_repository
        self._exploration_repository = exploration_repository

    def get_day_context(self, *, start: date, end: date) -> DayContextResponse:
        """Return canonical hover-context data for an inclusive date range."""

        event_days = self._exploration_repository.list_event_days(
            start_date=start,
            end_date=end,
        )
        asset_days = self._exploration_repository.list_asset_days(
            start_date=start,
            end_date=end,
        )
        person_links = self._exploration_repository.list_person_links(
            start_date=start,
            end_date=end,
        )
        tag_links = self._exploration_repository.list_tag_links(
            start_date=start,
            end_date=end,
        )
        map_points = self._exploration_repository.list_map_points(
            start_date=start,
            end_date=end,
        )

        event_counts = _count_items_by_day(event_days)
        asset_counts = _count_items_by_day(asset_days)
        persons_by_day = _build_day_context_persons(person_links)
        tags_by_day = _build_day_context_tags(tag_links)
        map_points_by_day = _build_day_context_map_points(map_points)

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
                for current_day in _iter_inclusive_dates(start, end)
            ],
        )

    def get_exploration(
        self,
        *,
        start: date | None,
        end: date | None,
        today: date,
    ) -> ExplorationResponse:
        """Return dense exploration bootstrap data for the resolved date window."""

        range_start, range_end = self._resolve_exploration_range(
            start=start,
            end=end,
            today=today,
        )
        overall_aggregate_map = {
            aggregate.date: aggregate
            for aggregate in self._daily_aggregate_repository.list_range(
                start_date=range_start,
                end_date=range_end,
            )
        }
        source_aggregate_map = _group_source_aggregates_by_day(
            self._daily_aggregate_repository.list_source_type_range(
                start_date=range_start,
                end_date=range_end,
            )
        )
        person_links = self._exploration_repository.list_person_links(
            start_date=range_start,
            end_date=range_end,
        )
        tag_links = self._exploration_repository.list_tag_links(
            start_date=range_start,
            end_date=range_end,
        )

        persons = _build_person_catalog(person_links)
        tags = _build_tag_catalog(tag_links)

        days = [
            _build_exploration_day(
                day=current_day,
                overall_aggregate_map=overall_aggregate_map,
                source_aggregate_map=source_aggregate_map,
            )
            for current_day in _iter_inclusive_dates(range_start, range_end)
        ]

        return ExplorationResponse(
            range=ExplorationRange(start=range_start, end=range_end),
            view_modes=get_default_view_modes(),
            persons=persons,
            tags=tags,
            days=days,
        )

    def _resolve_exploration_range(
        self,
        *,
        start: date | None,
        end: date | None,
        today: date,
    ) -> tuple[date, date]:
        """Resolve either the explicit range or a year-padded available range."""

        if start is not None and end is not None:
            return start, end

        bounds = self._daily_aggregate_repository.resolve_bounds()
        if bounds is None:
            return date(today.year, 1, 1), date(today.year, 12, 31)

        return (
            date(bounds.start_date.year, 1, 1),
            date(bounds.end_date.year, 12, 31),
        )


class DemoTimelineProjectionProvider:
    """Generate deterministic demo projections without reading production data."""

    def get_day_context(self, *, start: date, end: date) -> DayContextResponse:
        """Return canonical-style hover-context data for an inclusive date range."""

        days = [
            self._build_day_context_day(current_day)
            for current_day in _iter_inclusive_dates(start, end)
        ]
        return DayContextResponse(
            range=ExplorationRange(start=start, end=end),
            days=days,
        )

    def get_exploration(
        self,
        *,
        start: date | None,
        end: date | None,
        today: date,
    ) -> ExplorationResponse:
        """Return a deterministic multi-year exploration bootstrap payload."""

        del today
        range_start, range_end = self._resolve_exploration_range(
            start=start,
            end=end,
        )
        persons_by_id: dict[int, ExplorationPerson] = {}
        tags_by_path: dict[str, ExplorationTag] = {}
        days: list[ExplorationDay] = []

        for current_day in _iter_inclusive_dates(range_start, range_end):
            snapshot = self._build_day_snapshot(current_day)
            for person_id in snapshot.person_ids:
                person = _find_demo_person(person_id)
                persons_by_id[person_id] = ExplorationPerson(
                    id=person.id,
                    name=person.name,
                    role=person.role,
                )
            for tag_path in snapshot.tag_paths:
                tag = _find_demo_tag(tag_path)
                tags_by_path[tag_path] = ExplorationTag(
                    path=tag.path,
                    label=tag.label,
                )

            days.append(
                ExplorationDay(
                    date=current_day,
                    event_count=snapshot.event_count,
                    asset_count=snapshot.asset_count,
                    activity_score=snapshot.activity_score,
                    color_value=_get_activity_color_value(snapshot.activity_score),
                    has_data=snapshot.activity_score > 0,
                    person_ids=list(snapshot.person_ids),
                    tag_paths=list(snapshot.tag_paths),
                    derived_summary=ExplorationDayDerivedSummary(
                        tags=[
                            ExplorationDayTagSummary(
                                path=tag_path,
                                label=_find_demo_tag(tag_path).label,
                                count=1,
                            )
                            for tag_path in snapshot.tag_paths
                        ],
                        persons=[
                            ExplorationDayPersonSummary(
                                person_id=person_id,
                                name=_find_demo_person(person_id).name,
                                role=_find_demo_person(person_id).role,
                                count=1,
                            )
                            for person_id in snapshot.person_ids
                        ],
                        locations=[],
                        metadata={"projection_source": "demo"},
                    ),
                    source_summaries=[],
                )
            )

        return ExplorationResponse(
            range=ExplorationRange(start=range_start, end=range_end),
            view_modes=get_default_view_modes(),
            persons=sorted(
                persons_by_id.values(),
                key=lambda person: (person.name.casefold(), person.id),
            ),
            tags=sorted(
                tags_by_path.values(),
                key=lambda tag: (tag.path, tag.label.casefold()),
            ),
            days=days,
        )

    def _resolve_exploration_range(
        self,
        *,
        start: date | None,
        end: date | None,
    ) -> tuple[date, date]:
        """Return either the explicit range or the fixed multi-year demo window."""

        if start is not None and end is not None:
            return start, end
        return _DEMO_DEFAULT_RANGE

    def _build_day_context_day(self, day: date) -> DayContextDay:
        """Compose one hover-context payload for the given date."""

        snapshot = self._build_day_snapshot(day)
        return DayContextDay(
            date=day,
            persons=[
                ExplorationPerson(id=person.id, name=person.name, role=person.role)
                for person in sorted(
                    (_find_demo_person(person_id) for person_id in snapshot.person_ids),
                    key=lambda person: (person.name.casefold(), person.id),
                )
            ],
            tags=[
                ExplorationTag(path=tag.path, label=tag.label)
                for tag in sorted(
                    (_find_demo_tag(tag_path) for tag_path in snapshot.tag_paths),
                    key=lambda tag: (tag.path, tag.label.casefold()),
                )
            ],
            map_points=list(snapshot.map_points),
            summary_counts=DayContextSummaryCounts(
                events=snapshot.event_count,
                assets=snapshot.asset_count,
                places=len(snapshot.map_points),
            ),
        )

    def _build_day_snapshot(self, day: date) -> _DemoDaySnapshot:
        """Generate stable per-day demo data from calendar-driven signals."""

        ordinal = (day - _DEMO_REFERENCE_DATE).days
        weekday = day.weekday()
        is_weekend = weekday >= 5
        travel_cluster = ordinal % 61 in {0, 1, 2, 3, 4}
        sports_cluster = ordinal % 14 in {1, 4}
        family_cluster = ordinal % 11 == 0
        work_cluster = weekday < 5 and ordinal % 9 in {2, 3, 4}
        party_cluster = (ordinal + day.year) % 37 == 0
        outdoor_cluster = is_weekend and ordinal % 8 in {2, 3}
        quiet_cluster = ordinal % 17 == 0 and not (
            travel_cluster or sports_cluster or party_cluster
        )

        event_count = 1 if weekday < 5 and ordinal % 6 != 0 else 0
        asset_count = 1 if ordinal % 29 == 0 else 0

        if work_cluster:
            event_count += 1
        if travel_cluster:
            event_count += 2
            asset_count += 2
        if sports_cluster:
            event_count += 1
        if family_cluster and (is_weekend or asset_count > 0):
            asset_count += 1
        if party_cluster:
            event_count += 1
            asset_count += 1
        if outdoor_cluster:
            asset_count += 1
        if is_weekend and ordinal % 3 == 0:
            asset_count += 1
        if quiet_cluster:
            event_count = 0
            asset_count = 0

        if event_count == 0 and asset_count == 0:
            return _DemoDaySnapshot(
                event_count=0,
                asset_count=0,
                activity_score=0,
                person_ids=(),
                tag_paths=(),
                map_points=(),
            )

        activity_score = min(
            100,
            event_count * 16
            + asset_count * 12
            + (14 if travel_cluster else 0)
            + (10 if sports_cluster else 0)
            + (8 if party_cluster else 0)
            + (6 if outdoor_cluster else 0),
        )
        person_ids: set[int] = set()
        tag_paths: set[str] = set()

        if travel_cluster:
            person_ids.update({1, 2})
            tag_paths.add("travel/europe")
            if ordinal % 122 < 10:
                tag_paths.add("travel/weekender")
        if sports_cluster:
            person_ids.add(4)
            tag_paths.add("activity/sports/running")
        if outdoor_cluster:
            tag_paths.add("activity/outdoors")
        if family_cluster:
            person_ids.add(1)
            tag_paths.add("people/family")
        if work_cluster:
            person_ids.add(3)
            tag_paths.add("work/project-atlas")
        if party_cluster:
            person_ids.update({1, 5})
            tag_paths.add("social/house-party")
        if asset_count > 0 and not person_ids and ordinal % 23 == 0:
            person_ids.add(1)

        map_points = self._build_map_points(
            day=day,
            ordinal=ordinal,
            travel_cluster=travel_cluster,
            sports_cluster=sports_cluster,
            family_cluster=family_cluster,
            party_cluster=party_cluster,
            outdoor_cluster=outdoor_cluster,
            asset_count=asset_count,
        )

        return _DemoDaySnapshot(
            event_count=event_count,
            asset_count=asset_count,
            activity_score=activity_score,
            person_ids=tuple(sorted(person_ids)),
            tag_paths=tuple(sorted(tag_paths)),
            map_points=map_points,
        )

    def _build_map_points(
        self,
        *,
        day: date,
        ordinal: int,
        travel_cluster: bool,
        sports_cluster: bool,
        family_cluster: bool,
        party_cluster: bool,
        outdoor_cluster: bool,
        asset_count: int,
    ) -> tuple[DayContextMapPoint, ...]:
        """Generate stable real-coordinate map points for a day."""

        locations: list[_DemoLocationDefinition] = []
        base_index = (ordinal + day.year) % len(_DEMO_LOCATIONS)

        if travel_cluster:
            locations.append(_DEMO_LOCATIONS[base_index])
            locations.append(_DEMO_LOCATIONS[(base_index + 3) % len(_DEMO_LOCATIONS)])
        elif sports_cluster:
            locations.append(_DEMO_LOCATIONS[(base_index + 1) % len(_DEMO_LOCATIONS)])
        elif party_cluster:
            locations.append(_DEMO_LOCATIONS[(base_index + 2) % len(_DEMO_LOCATIONS)])
        elif outdoor_cluster or family_cluster:
            locations.append(_DEMO_LOCATIONS[(base_index + 4) % len(_DEMO_LOCATIONS)])
        elif asset_count > 0 and ordinal % 5 == 0:
            locations.append(_DEMO_LOCATIONS[(base_index + 5) % len(_DEMO_LOCATIONS)])

        return tuple(
            DayContextMapPoint(
                id=f"demo:{day.isoformat()}:{location.slug}:{index}",
                label=location.label,
                latitude=location.latitude,
                longitude=location.longitude,
            )
            for index, location in enumerate(locations, start=1)
        )


def get_default_view_modes() -> list[ExplorationViewMode]:
    """Return the backend-defined exploration view modes."""

    return [
        ExplorationViewMode(
            id=mode_id,
            label=label,
            description=description,
        )
        for mode_id, label, description in _VIEW_MODE_DEFINITIONS
    ]


def _build_exploration_day(
    *,
    day: date,
    overall_aggregate_map: dict[date, DailyAggregateReadSnapshot],
    source_aggregate_map: dict[date, list[DailyAggregateReadSnapshot]],
) -> ExplorationDay:
    """Compose a single dense exploration day."""

    aggregate = overall_aggregate_map.get(day)
    source_aggregates = source_aggregate_map.get(day, [])
    event_count = aggregate.total_events if aggregate is not None else 0
    asset_count = aggregate.media_count if aggregate is not None else 0
    activity_score = aggregate.activity_score if aggregate is not None else 0
    person_ids = (
        _extract_person_ids_from_summary(aggregate.person_summary_json)
        if aggregate is not None
        else []
    )
    tag_paths = (
        _extract_tag_paths_from_summary(aggregate.tag_summary_json)
        if aggregate is not None
        else []
    )
    has_data = event_count > 0 or asset_count > 0 or activity_score > 0

    return ExplorationDay(
        date=day,
        event_count=event_count,
        asset_count=asset_count,
        activity_score=activity_score,
        color_value=_get_activity_color_value(activity_score),
        has_data=has_data,
        person_ids=person_ids,
        tag_paths=tag_paths,
        derived_summary=_build_derived_summary(aggregate),
        source_summaries=[
            _build_source_summary(source_aggregate)
            for source_aggregate in source_aggregates
        ],
    )


def _group_source_aggregates_by_day(
    snapshots: list[DailyAggregateReadSnapshot],
) -> dict[date, list[DailyAggregateReadSnapshot]]:
    """Group connector-scoped derived aggregates by day."""

    grouped: dict[date, list[DailyAggregateReadSnapshot]] = defaultdict(list)
    for snapshot in snapshots:
        grouped[snapshot.date].append(snapshot)

    return {
        day: sorted(day_snapshots, key=lambda snapshot: snapshot.source_type)
        for day, day_snapshots in grouped.items()
    }


def _build_source_summary(
    snapshot: DailyAggregateReadSnapshot,
) -> ExplorationDaySourceSummary:
    """Map a connector-scoped aggregate row to the exploration contract."""

    return ExplorationDaySourceSummary(
        source_type=snapshot.source_type,
        event_count=snapshot.total_events,
        asset_count=snapshot.media_count,
        activity_score=snapshot.activity_score,
        color_value=_get_activity_color_value(snapshot.activity_score),
        has_data=snapshot.activity_score > 0,
        person_ids=_extract_person_ids_from_summary(snapshot.person_summary_json),
        tag_paths=_extract_tag_paths_from_summary(snapshot.tag_summary_json),
        derived_summary=_build_derived_summary(snapshot),
    )


def _build_derived_summary(
    snapshot: DailyAggregateReadSnapshot | None,
) -> ExplorationDayDerivedSummary:
    """Return the exploration-facing semantic summary for one derived row."""

    if snapshot is None:
        return ExplorationDayDerivedSummary(
            tags=[],
            persons=[],
            locations=[],
            metadata={},
        )

    return ExplorationDayDerivedSummary(
        tags=[
            ExplorationDayTagSummary(
                path=summary["path"],
                label=summary["label"],
                count=summary["count"],
            )
            for summary in snapshot.tag_summary_json
            if _is_tag_summary(summary)
        ],
        persons=[
            ExplorationDayPersonSummary(
                person_id=summary["person_id"],
                name=summary["name"],
                role=summary["role"],
                count=summary["count"],
            )
            for summary in snapshot.person_summary_json
            if _is_person_summary(summary)
        ],
        locations=[
            ExplorationDayLocationSummary(
                label=summary["label"],
                latitude=summary["latitude"],
                longitude=summary["longitude"],
                count=summary["count"],
            )
            for summary in snapshot.location_summary_json
            if _is_location_summary(summary)
        ],
        metadata=dict(snapshot.metadata_json),
    )


def _extract_person_ids_from_summary(
    summaries: list[dict[str, object]],
) -> list[int]:
    """Extract person identifiers from a derived person summary payload."""

    return [
        summary["person_id"]
        for summary in summaries
        if _is_person_summary(summary)
    ]


def _extract_tag_paths_from_summary(
    summaries: list[dict[str, object]],
) -> list[str]:
    """Extract tag paths from a derived tag summary payload."""

    return [
        summary["path"]
        for summary in summaries
        if _is_tag_summary(summary)
    ]


def _is_tag_summary(summary: object) -> bool:
    """Return whether an object matches the derived tag summary shape."""

    return (
        isinstance(summary, dict)
        and isinstance(summary.get("path"), str)
        and isinstance(summary.get("label"), str)
        and isinstance(summary.get("count"), int)
    )


def _is_person_summary(summary: object) -> bool:
    """Return whether an object matches the derived person summary shape."""

    return (
        isinstance(summary, dict)
        and isinstance(summary.get("person_id"), int)
        and isinstance(summary.get("name"), str)
        and isinstance(summary.get("count"), int)
        and (
            summary.get("role") is None or isinstance(summary.get("role"), str)
        )
    )


def _is_location_summary(summary: object) -> bool:
    """Return whether an object matches the derived location summary shape."""

    return (
        isinstance(summary, dict)
        and isinstance(summary.get("label"), str)
        and isinstance(summary.get("latitude"), (int, float))
        and isinstance(summary.get("longitude"), (int, float))
        and isinstance(summary.get("count"), int)
    )


def _count_items_by_day(snapshots: list[DayActivityItemSnapshot]) -> dict[date, int]:
    """Count canonical timeline items per UTC day."""

    counts: dict[date, int] = defaultdict(int)
    for snapshot in snapshots:
        counts[snapshot.day] += 1
    return dict(counts)


def _build_person_catalog(
    links: list[DayPersonLinkSnapshot],
) -> list[ExplorationPerson]:
    """Build the visible person catalog from canonical associations."""

    persons_by_id: dict[int, ExplorationPerson] = {}

    for link in links:
        persons_by_id.setdefault(
            link.person_id,
            ExplorationPerson(
                id=link.person_id,
                name=link.person_name,
                role=link.person_role,
            ),
        )

    persons = sorted(
        persons_by_id.values(),
        key=lambda person: (person.name.casefold(), person.id),
    )
    return persons


def _build_tag_catalog(
    links: list[DayTagLinkSnapshot],
) -> list[ExplorationTag]:
    """Build the visible tag catalog from canonical associations."""

    tags_by_path: dict[str, ExplorationTag] = {}

    for link in links:
        tags_by_path.setdefault(
            link.tag_path,
            ExplorationTag(path=link.tag_path, label=link.tag_label),
        )

    tags = sorted(
        tags_by_path.values(),
        key=lambda tag: (tag.path, tag.label.casefold()),
    )
    return tags


def _build_day_context_persons(
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


def _build_day_context_tags(
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


def _build_day_context_map_points(
    snapshots: list[DayMapPointSnapshot],
) -> dict[date, list[DayContextMapPoint]]:
    """Build sorted per-day map points for hover context."""

    points_by_day: dict[date, list[DayContextMapPoint]] = defaultdict(list)

    for snapshot in snapshots:
        points_by_day[snapshot.day].append(
            DayContextMapPoint(
                id=f"{snapshot.item_type}:{snapshot.item_id}",
                label=_resolve_map_point_label(snapshot),
                latitude=snapshot.latitude,
                longitude=snapshot.longitude,
            )
        )

    return dict(points_by_day)


def _iter_inclusive_dates(start: date, end: date) -> list[date]:
    """Return every UTC calendar date in the inclusive range."""

    days: list[date] = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def _get_activity_color_value(activity_score: int) -> str:
    """Map an activity score to the shared heatmap intensity token."""

    if activity_score <= 0:
        return "empty"
    if activity_score < 35:
        return "low"
    if activity_score < 70:
        return "medium"
    return "high"


def _resolve_map_point_label(snapshot: DayMapPointSnapshot) -> str:
    """Return a stable display label for a coordinate-bearing canonical item."""

    if snapshot.label is not None:
        normalized = snapshot.label.strip()
        if normalized:
            return normalized

    if snapshot.fallback_identifier is not None:
        normalized_identifier = snapshot.fallback_identifier.strip()
        if normalized_identifier:
            return normalized_identifier

    return f"{_humanize_label(snapshot.fallback_type)} #{snapshot.item_id}"


def _humanize_label(value: str) -> str:
    """Convert a canonical type token into a lightweight display label."""

    parts = [part for part in value.replace("-", "_").split("_") if part]
    if not parts:
        return "Item"
    return " ".join(part.capitalize() for part in parts)


def _find_demo_person(person_id: int) -> _DemoPersonDefinition:
    """Return the configured demo person definition for the given identifier."""

    for person in _DEMO_PERSONS:
        if person.id == person_id:
            return person
    raise KeyError(f"unknown demo person id: {person_id}")


def _find_demo_tag(tag_path: str) -> _DemoTagDefinition:
    """Return the configured demo tag definition for the given path."""

    for tag in _DEMO_TAGS:
        if tag.path == tag_path:
            return tag
    raise KeyError(f"unknown demo tag path: {tag_path}")


_DEMO_PERSONS: Final[tuple[_DemoPersonDefinition, ...]] = (
    _DemoPersonDefinition(id=1, name="Anna", role="Family"),
    _DemoPersonDefinition(id=2, name="Milo", role="Travel buddy"),
    _DemoPersonDefinition(id=3, name="Luca", role="Work"),
    _DemoPersonDefinition(id=4, name="Nora", role="Coach"),
    _DemoPersonDefinition(id=5, name="Emma", role="Friend"),
)

_DEMO_TAGS: Final[tuple[_DemoTagDefinition, ...]] = (
    _DemoTagDefinition(path="activity/outdoors", label="Outdoors"),
    _DemoTagDefinition(path="activity/sports/running", label="Running"),
    _DemoTagDefinition(path="people/family", label="Family"),
    _DemoTagDefinition(path="social/house-party", label="House Party"),
    _DemoTagDefinition(path="travel/europe", label="Europe"),
    _DemoTagDefinition(path="travel/weekender", label="Weekend Escape"),
    _DemoTagDefinition(path="work/project-atlas", label="Project Atlas"),
)

_DEMO_LOCATIONS: Final[tuple[_DemoLocationDefinition, ...]] = (
    _DemoLocationDefinition(
        slug="berlin",
        label="Berlin",
        latitude=52.52,
        longitude=13.405,
    ),
    _DemoLocationDefinition(
        slug="potsdam",
        label="Potsdam",
        latitude=52.3906,
        longitude=13.0645,
    ),
    _DemoLocationDefinition(
        slug="venice",
        label="Venice",
        latitude=45.4408,
        longitude=12.3155,
    ),
    _DemoLocationDefinition(
        slug="munich",
        label="Munich",
        latitude=48.1372,
        longitude=11.5756,
    ),
    _DemoLocationDefinition(
        slug="zurich",
        label="Zurich",
        latitude=47.3769,
        longitude=8.5417,
    ),
    _DemoLocationDefinition(
        slug="prague",
        label="Prague",
        latitude=50.0755,
        longitude=14.4378,
    ),
    _DemoLocationDefinition(
        slug="hamburg",
        label="Hamburg",
        latitude=53.5511,
        longitude=9.9937,
    ),
    _DemoLocationDefinition(
        slug="leipzig",
        label="Leipzig",
        latitude=51.3397,
        longitude=12.3731,
    ),
    _DemoLocationDefinition(
        slug="rome",
        label="Rome",
        latitude=41.9028,
        longitude=12.4964,
    ),
    _DemoLocationDefinition(
        slug="paris",
        label="Paris",
        latitude=48.8566,
        longitude=2.3522,
    ),
)
