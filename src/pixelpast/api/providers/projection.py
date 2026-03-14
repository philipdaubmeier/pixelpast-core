"""Projection providers for exploration-oriented API responses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Final, Protocol

from pixelpast.api.providers.bootstrap_ui import build_bootstrap_response, get_default_view_modes
from pixelpast.api.providers.daygrid import (
    ExplorationGridFilters,
    build_grid_day_from_snapshot,
    build_grid_response,
)
from pixelpast.api.providers.hovercontext import build_day_context_response
from pixelpast.api.schemas import (
    DayContextDay,
    DayContextMapPoint,
    DayContextResponse,
    DayContextSummaryCounts,
    ExplorationBootstrapResponse,
    ExplorationGridResponse,
    ExplorationPerson,
    ExplorationRange,
    ExplorationTag,
)
from pixelpast.persistence.repositories import (
    DailyAggregateReadRepository,
    ExplorationReadRepository,
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

        return build_day_context_response(
            start=start,
            end=end,
            event_days=self._exploration_repository.list_event_days(
                start_date=start,
                end_date=end,
            ),
            asset_days=self._exploration_repository.list_asset_days(
                start_date=start,
                end_date=end,
            ),
            person_links=self._exploration_repository.list_person_links(
                start_date=start,
                end_date=end,
            ),
            tag_links=self._exploration_repository.list_tag_links(
                start_date=start,
                end_date=end,
            ),
            map_points=self._exploration_repository.list_map_points(
                start_date=start,
                end_date=end,
            ),
            days=iter_inclusive_dates(start, end),
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
        return build_bootstrap_response(
            start=range_start,
            end=range_end,
            person_links=self._exploration_repository.list_person_links(
                start_date=range_start,
                end_date=range_end,
            ),
            tag_links=self._exploration_repository.list_tag_links(
                start_date=range_start,
                end_date=range_end,
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
        return build_grid_response(
            start=range_start,
            end=range_end,
            aggregate_map=aggregate_map,
            filters=filters,
            days=iter_inclusive_dates(range_start, range_end),
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
            for current_day in iter_inclusive_dates(start, end)
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

        for current_day in iter_inclusive_dates(range_start, range_end):
            snapshot = self._build_day_snapshot(current_day)
            for person_id in snapshot.person_ids:
                person = find_demo_person(person_id)
                persons_by_id[person_id] = ExplorationPerson(
                    id=person.id,
                    name=person.name,
                    role=person.role,
                )
            for tag_path in snapshot.tag_paths:
                tag = find_demo_tag(tag_path)
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
                build_grid_day_from_snapshot(
                    day=current_day,
                    activity_score=(snapshot := self._build_day_snapshot(current_day)).activity_score,
                    event_count=snapshot.event_count,
                    asset_count=snapshot.asset_count,
                    person_ids=list(snapshot.person_ids),
                    tag_paths=list(snapshot.tag_paths),
                    filters=filters,
                )
                for current_day in iter_inclusive_dates(range_start, range_end)
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
                    (find_demo_person(person_id) for person_id in snapshot.person_ids),
                    key=lambda person: (person.name.casefold(), person.id),
                )
            ],
            tags=[
                ExplorationTag(path=tag.path, label=tag.label)
                for tag in sorted(
                    (find_demo_tag(tag_path) for tag_path in snapshot.tag_paths),
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


def iter_inclusive_dates(start: date, end: date) -> list[date]:
    """Return every UTC calendar date in the inclusive range."""

    days: list[date] = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def find_demo_person(person_id: int) -> _DemoPersonDefinition:
    """Return the configured demo person definition for the given identifier."""

    for person in _DEMO_PERSONS:
        if person.id == person_id:
            return person
    raise KeyError(f"unknown demo person id: {person_id}")


def find_demo_tag(tag_path: str) -> _DemoTagDefinition:
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
