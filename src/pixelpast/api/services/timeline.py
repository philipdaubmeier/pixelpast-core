"""Service layer for timeline-oriented read endpoints."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Final

from pixelpast.api.schemas import (
    DayAssetItem,
    DayDetailResponse,
    DayEventItem,
    ExplorationDay,
    ExplorationPerson,
    ExplorationRange,
    ExplorationResponse,
    ExplorationTag,
    ExplorationViewMode,
    HeatmapDay,
    HeatmapResponse,
)
from pixelpast.persistence.repositories import (
    DayActivityItemSnapshot,
    DayPersonLinkSnapshot,
    DayTagLinkSnapshot,
    DailyAggregateReadRepository,
    DayTimelineItemSnapshot,
    DayTimelineRepository,
    ExplorationReadRepository,
)

_VIEW_MODE_DEFINITIONS: Final[tuple[ExplorationViewMode, ...]] = (
    ExplorationViewMode(
        id="activity",
        label="Activity",
        description="Default heat intensity across all timeline sources.",
    ),
    ExplorationViewMode(
        id="travel",
        label="Travel",
        description="Highlights movement-heavy and location-rich days.",
    ),
    ExplorationViewMode(
        id="sports",
        label="Sports",
        description="Reserves the grid for workout and fitness projections.",
    ),
    ExplorationViewMode(
        id="party_probability",
        label="Social",
        description="Placeholder derived view for future social-density signals.",
    ),
)


class TimelineQueryService:
    """Compose read repositories into explicit API response models."""

    def __init__(
        self,
        *,
        daily_aggregate_repository: DailyAggregateReadRepository,
        day_timeline_repository: DayTimelineRepository,
        exploration_repository: ExplorationReadRepository,
    ) -> None:
        self._daily_aggregate_repository = daily_aggregate_repository
        self._day_timeline_repository = day_timeline_repository
        self._exploration_repository = exploration_repository

    def get_heatmap(self, *, start: date, end: date) -> HeatmapResponse:
        """Return the heatmap projection for an inclusive date range."""

        aggregates = self._daily_aggregate_repository.list_range(
            start_date=start,
            end_date=end,
        )
        return HeatmapResponse(
            start=start,
            end=end,
            days=[
                HeatmapDay(
                    date=aggregate.date,
                    total_events=aggregate.total_events,
                    media_count=aggregate.media_count,
                    activity_score=aggregate.activity_score,
                )
                for aggregate in aggregates
            ],
        )

    def get_day_detail(self, *, day: date) -> DayDetailResponse:
        """Return a unified, time-ordered day projection."""

        snapshots = self._day_timeline_repository.list_day(day=day)
        return DayDetailResponse(
            date=day,
            items=[self._map_day_item(snapshot) for snapshot in snapshots],
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
        aggregate_map = {
            aggregate.date: aggregate
            for aggregate in self._daily_aggregate_repository.list_range(
                start_date=range_start,
                end_date=range_end,
            )
        }
        event_days = self._exploration_repository.list_event_days(
            start_date=range_start,
            end_date=range_end,
        )
        asset_days = self._exploration_repository.list_asset_days(
            start_date=range_start,
            end_date=range_end,
        )
        person_links = self._exploration_repository.list_person_links(
            start_date=range_start,
            end_date=range_end,
        )
        tag_links = self._exploration_repository.list_tag_links(
            start_date=range_start,
            end_date=range_end,
        )

        event_counts = self._count_items_by_day(event_days)
        asset_counts = self._count_items_by_day(asset_days)
        person_ids_by_day, person_names_by_day, persons = self._build_person_catalog(
            person_links
        )
        tag_paths_by_day, tags = self._build_tag_catalog(tag_links)

        days = [
            self._build_exploration_day(
                day=current_day,
                aggregate_map=aggregate_map,
                event_counts=event_counts,
                asset_counts=asset_counts,
                person_ids_by_day=person_ids_by_day,
                person_names_by_day=person_names_by_day,
                tag_paths_by_day=tag_paths_by_day,
            )
            for current_day in _iter_inclusive_dates(range_start, range_end)
        ]

        return ExplorationResponse(
            range=ExplorationRange(start=range_start, end=range_end),
            view_modes=list(_VIEW_MODE_DEFINITIONS),
            persons=persons,
            tags=tags,
            days=days,
        )

    def _map_day_item(
        self,
        snapshot: DayTimelineItemSnapshot,
    ) -> DayEventItem | DayAssetItem:
        """Map repository snapshots to discriminated API items."""

        if snapshot.item_type == "event":
            return DayEventItem(
                item_type="event",
                id=snapshot.id,
                timestamp=snapshot.timestamp,
                event_type=snapshot.type,
                title=snapshot.title,
                summary=snapshot.summary,
            )

        return DayAssetItem(
            item_type="asset",
            id=snapshot.id,
            timestamp=snapshot.timestamp,
            media_type=snapshot.type,
            external_id=snapshot.external_id,
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

        bounds = self._exploration_repository.resolve_timeline_bounds()
        if bounds is None:
            return date(today.year, 1, 1), date(today.year, 12, 31)

        return (
            date(bounds.start_date.year, 1, 1),
            date(bounds.end_date.year, 12, 31),
        )

    def _count_items_by_day(
        self,
        snapshots: list[DayActivityItemSnapshot],
    ) -> dict[date, int]:
        """Count canonical timeline items per UTC day."""

        counts: dict[date, int] = defaultdict(int)
        for snapshot in snapshots:
            counts[snapshot.day] += 1
        return dict(counts)

    def _build_person_catalog(
        self,
        links: list[DayPersonLinkSnapshot],
    ) -> tuple[dict[date, list[int]], dict[date, list[str]], list[ExplorationPerson]]:
        """Build dense day-to-person ids plus the visible person catalog."""

        person_ids_by_day: dict[date, set[int]] = defaultdict(set)
        person_names_by_day: dict[date, set[str]] = defaultdict(set)
        persons_by_id: dict[int, ExplorationPerson] = {}

        for link in links:
            person_ids_by_day[link.day].add(link.person_id)
            person_names_by_day[link.day].add(link.person_name)
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
        return (
            {
                day: sorted(person_ids)
                for day, person_ids in person_ids_by_day.items()
            },
            {
                day: sorted(person_names, key=str.casefold)
                for day, person_names in person_names_by_day.items()
            },
            persons,
        )

    def _build_tag_catalog(
        self,
        links: list[DayTagLinkSnapshot],
    ) -> tuple[dict[date, list[str]], list[ExplorationTag]]:
        """Build dense day-to-tag paths plus the visible tag catalog."""

        tag_paths_by_day: dict[date, set[str]] = defaultdict(set)
        tags_by_path: dict[str, ExplorationTag] = {}

        for link in links:
            tag_paths_by_day[link.day].add(link.tag_path)
            tags_by_path.setdefault(
                link.tag_path,
                ExplorationTag(path=link.tag_path, label=link.tag_label),
            )

        tags = sorted(
            tags_by_path.values(),
            key=lambda tag: (tag.path, tag.label.casefold()),
        )
        return (
            {
                day: sorted(tag_paths)
                for day, tag_paths in tag_paths_by_day.items()
            },
            tags,
        )

    def _build_exploration_day(
        self,
        *,
        day: date,
        aggregate_map,
        event_counts: dict[date, int],
        asset_counts: dict[date, int],
        person_ids_by_day: dict[date, list[int]],
        person_names_by_day: dict[date, list[str]],
        tag_paths_by_day: dict[date, list[str]],
    ) -> ExplorationDay:
        """Compose a single dense exploration day."""

        aggregate = aggregate_map.get(day)
        event_count = (
            aggregate.total_events if aggregate is not None else event_counts.get(day, 0)
        )
        asset_count = (
            aggregate.media_count if aggregate is not None else asset_counts.get(day, 0)
        )
        activity_score = (
            aggregate.activity_score
            if aggregate is not None
            else event_count + asset_count
        )
        person_ids = person_ids_by_day.get(day, [])
        person_names = person_names_by_day.get(day, [])
        tag_paths = tag_paths_by_day.get(day, [])
        has_data = event_count > 0 or asset_count > 0 or activity_score > 0
        color_value = _get_activity_color_value(activity_score)

        return ExplorationDay(
            date=day,
            event_count=event_count,
            asset_count=asset_count,
            activity_score=activity_score,
            color_value=color_value,
            has_data=has_data,
            person_ids=person_ids,
            tag_paths=tag_paths,
            view_mode_color_values={
                "activity": color_value,
                "travel": _get_travel_color_value(
                    activity_score=activity_score,
                    person_names=person_names,
                    tag_paths=tag_paths,
                ),
                "sports": _get_sports_color_value(
                    activity_score=activity_score,
                    tag_paths=tag_paths,
                ),
                "party_probability": _get_party_probability_color_value(
                    person_ids=person_ids,
                    tag_paths=tag_paths,
                ),
            },
        )


def _iter_inclusive_dates(start: date, end: date) -> list[date]:
    """Return every UTC calendar date in the inclusive range."""

    days: list[date] = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def _get_activity_color_value(activity_score: int) -> str:
    """Port the default frontend heatmap intensity thresholds."""

    if activity_score <= 0:
        return "empty"
    if activity_score < 35:
        return "low"
    if activity_score < 70:
        return "medium"
    return "high"


def _get_travel_color_value(
    *,
    activity_score: int,
    person_names: list[str],
    tag_paths: list[str],
) -> str:
    """Port the current frontend travel view heuristic."""

    if any(tag_path.startswith("travel/") for tag_path in tag_paths):
        return "high"
    if any(person_name.casefold() == "milo" for person_name in person_names):
        return "medium"
    return "low" if activity_score >= 55 else "empty"


def _get_sports_color_value(*, activity_score: int, tag_paths: list[str]) -> str:
    """Port the current frontend sports view heuristic."""

    if any(tag_path.startswith("activity/") for tag_path in tag_paths):
        return "high"
    if activity_score >= 78:
        return "medium"
    return "low" if activity_score >= 60 else "empty"


def _get_party_probability_color_value(
    *,
    person_ids: list[int],
    tag_paths: list[str],
) -> str:
    """Port the current frontend social-density heuristic."""

    if len(person_ids) >= 2:
        return "high"
    if len(person_ids) == 1:
        return "medium"
    return (
        "low"
        if any(tag_path.startswith("people/") for tag_path in tag_paths)
        else "empty"
    )
