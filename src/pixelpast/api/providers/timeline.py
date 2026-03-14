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
    ExplorationBootstrapResponse,
    ExplorationGridDay,
    ExplorationGridResponse,
    ExplorationPerson,
    ExplorationRange,
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

    def get_exploration_bootstrap(
        self,
        *,
        start: date | None,
        end: date | None,
        today: date,
    ) -> ExplorationBootstrapResponse:
        """Return lightweight shell metadata for the resolved exploration range."""
        ...

    def get_exploration_grid(
        self,
        *,
        start: date | None,
        end: date | None,
        today: date,
        filters: ExplorationGridFilters,
    ) -> ExplorationGridResponse:
        """Return derived-only dense day activity for the resolved exploration range."""
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

    def get_exploration_bootstrap(
        self,
        *,
        start: date | None,
        end: date | None,
        today: date,
    ) -> ExplorationBootstrapResponse:
        """Return shell metadata for the resolved exploration range."""

        range_start, range_end = self._resolve_exploration_range(
            start=start,
            end=end,
            today=today,
        )
        person_links = self._exploration_repository.list_person_links(
            start_date=range_start,
            end_date=range_end,
        )
        tag_links = self._exploration_repository.list_tag_links(
            start_date=range_start,
            end_date=range_end,
        )

        return ExplorationBootstrapResponse(
            range=ExplorationRange(start=range_start, end=range_end),
            view_modes=get_default_view_modes(),
            persons=_build_person_catalog(person_links),
            tags=_build_tag_catalog(tag_links),
        )

    def get_exploration_grid(
        self,
        *,
        start: date | None,
        end: date | None,
        today: date,
        filters: ExplorationGridFilters,
    ) -> ExplorationGridResponse:
        """Return a derived-only dense grid with server-side persistent filters."""

        range_start, range_end = self._resolve_exploration_range(
            start=start,
            end=end,
            today=today,
        )
        aggregate_map = {
            aggregate.date: aggregate
            for aggregate in self._daily_aggregate_repository.list_range(
                start_date=range_start,
                end_date=range_end,
            )
        }

        return ExplorationGridResponse(
            range=ExplorationRange(start=range_start, end=range_end),
            days=[
                _build_grid_day_from_aggregate(
                    day=current_day,
                    aggregate=aggregate_map.get(current_day),
                    filters=filters,
                )
                for current_day in _iter_inclusive_dates(range_start, range_end)
            ],
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

    def get_exploration_bootstrap(
        self,
        *,
        start: date | None,
        end: date | None,
        today: date,
    ) -> ExplorationBootstrapResponse:
        """Return a deterministic exploration shell payload."""

        del today
        range_start, range_end = self._resolve_exploration_range(
            start=start,
            end=end,
        )
        persons_by_id: dict[int, ExplorationPerson] = {}
        tags_by_path: dict[str, ExplorationTag] = {}

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

        return ExplorationBootstrapResponse(
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
        )

    def get_exploration_grid(
        self,
        *,
        start: date | None,
        end: date | None,
        today: date,
        filters: ExplorationGridFilters,
    ) -> ExplorationGridResponse:
        """Return a deterministic derived-only exploration grid payload."""

        del today
        range_start, range_end = self._resolve_exploration_range(
            start=start,
            end=end,
        )

        return ExplorationGridResponse(
            range=ExplorationRange(start=range_start, end=range_end),
            days=[
                _build_grid_day_from_snapshot(
                    day=current_day,
                    snapshot=self._build_day_snapshot(current_day),
                    filters=filters,
                )
                for current_day in _iter_inclusive_dates(range_start, range_end)
            ],
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


def _build_grid_day_from_aggregate(
    *,
    day: date,
    aggregate: DailyAggregateReadSnapshot | None,
    filters: ExplorationGridFilters,
) -> ExplorationGridDay:
    """Compose one dense grid day from an overall derived aggregate row."""

    if aggregate is None:
        return _empty_grid_day(day)

    person_ids = _extract_person_ids_from_summary(aggregate.person_summary_json)
    tag_paths = _extract_tag_paths_from_summary(aggregate.tag_summary_json)
    has_data = (
        aggregate.total_events > 0
        or aggregate.media_count > 0
        or aggregate.activity_score > 0
    )
    if not has_data or not _matches_grid_filters(
        filters=filters,
        person_ids=person_ids,
        tag_paths=tag_paths,
    ):
        return _empty_grid_day(day)

    return ExplorationGridDay(
        date=day,
        activity_score=aggregate.activity_score,
        color_value=_get_view_mode_color_value(
            view_mode=filters.view_mode,
            activity_score=aggregate.activity_score,
            person_ids=person_ids,
            tag_paths=tag_paths,
        ),
        has_data=True,
    )


def _build_grid_day_from_snapshot(
    *,
    day: date,
    snapshot: _DemoDaySnapshot,
    filters: ExplorationGridFilters,
) -> ExplorationGridDay:
    """Compose one dense grid day from deterministic demo data."""

    has_data = (
        snapshot.event_count > 0
        or snapshot.asset_count > 0
        or snapshot.activity_score > 0
    )
    if not has_data or not _matches_grid_filters(
        filters=filters,
        person_ids=list(snapshot.person_ids),
        tag_paths=list(snapshot.tag_paths),
    ):
        return _empty_grid_day(day)

    return ExplorationGridDay(
        date=day,
        activity_score=snapshot.activity_score,
        color_value=_get_view_mode_color_value(
            view_mode=filters.view_mode,
            activity_score=snapshot.activity_score,
            person_ids=list(snapshot.person_ids),
            tag_paths=list(snapshot.tag_paths),
        ),
        has_data=True,
    )


def _empty_grid_day(day: date) -> ExplorationGridDay:
    """Return the canonical empty exploration-grid payload."""

    return ExplorationGridDay(
        date=day,
        activity_score=0,
        color_value="empty",
        has_data=False,
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

    return sorted(
        persons_by_id.values(),
        key=lambda person: (person.name.casefold(), person.id),
    )


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

    return sorted(
        tags_by_path.values(),
        key=lambda tag: (tag.path, tag.label.casefold()),
    )


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


def _matches_grid_filters(
    *,
    filters: ExplorationGridFilters,
    person_ids: list[int],
    tag_paths: list[str],
) -> bool:
    """Return whether a derived day matches the server-owned persistent filters."""

    if filters.person_ids and not set(person_ids).intersection(filters.person_ids):
        return False

    if filters.tag_paths and not any(
        _tag_path_matches_selection(day_tag_path=day_tag_path, selected_tag_path=tag_path)
        for day_tag_path in tag_paths
        for tag_path in filters.tag_paths
    ):
        return False

    # Additional filter fields stay backend-owned even before they are fully
    # implemented as database predicates, so the client no longer owns this flow.
    return True


def _tag_path_matches_selection(
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


def _get_view_mode_color_value(
    *,
    view_mode: str,
    activity_score: int,
    person_ids: list[int],
    tag_paths: list[str],
) -> str:
    """Resolve the server-side color token for the requested exploration mode."""

    if view_mode == "activity":
        return _get_activity_color_value(activity_score)

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

    return _get_activity_color_value(activity_score)


def _get_activity_color_value(activity_score: int) -> str:
    """Map an activity score to the shared heatmap intensity token."""

    if activity_score <= 0:
        return "empty"
    if activity_score < 35:
        return "low"
    if activity_score < 70:
        return "medium"
    return "high"


def _extract_person_ids_from_summary(
    summaries: list[dict[str, object]],
) -> list[int]:
    """Extract person identifiers from a derived person summary payload."""

    return [summary["person_id"] for summary in summaries if _is_person_summary(summary)]


def _extract_tag_paths_from_summary(
    summaries: list[dict[str, object]],
) -> list[str]:
    """Extract tag paths from a derived tag summary payload."""

    return [summary["path"] for summary in summaries if _is_tag_summary(summary)]


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
        and (summary.get("role") is None or isinstance(summary.get("role"), str))
    )


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
