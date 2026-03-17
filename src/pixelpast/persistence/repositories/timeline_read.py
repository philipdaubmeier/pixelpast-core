"""Read repositories for timeline and exploration API projections."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pixelpast.persistence.models import (
    Asset,
    AssetPerson,
    AssetTag,
    DAILY_AGGREGATE_OVERALL_SOURCE_TYPE,
    DAILY_AGGREGATE_SCOPE_OVERALL,
    DAILY_AGGREGATE_SCOPE_SOURCE_TYPE,
    DailyAggregate,
    DailyView,
    Event,
    EventPerson,
    EventTag,
    Person,
    Source,
    Tag,
)
from pixelpast.persistence.repositories.daily_aggregates import _apply_datetime_range


@dataclass(slots=True, frozen=True)
class DailyAggregateReadSnapshot:
    """Serializable read-model payload for one derived daily aggregate row."""

    date: date
    total_events: int
    media_count: int
    activity_score: int
    color_value: str | None
    title: str | None
    aggregate_scope: str
    source_type: str
    tag_summary_json: list[dict[str, Any]]
    person_summary_json: list[dict[str, Any]]
    location_summary_json: list[dict[str, Any]]
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class TimelineBoundsSnapshot:
    """Serializable bounds for the available explorable timeline."""

    start_date: date
    end_date: date


@dataclass(slots=True, frozen=True)
class DailyViewCatalogSnapshot:
    """Serializable exploration-view catalog entry."""

    view_id: str
    label: str
    description: str


@dataclass(slots=True, frozen=True)
class DayActivityItemSnapshot:
    """Serializable per-item UTC day placement."""

    id: int
    day: date


@dataclass(slots=True, frozen=True)
class DayPersonLinkSnapshot:
    """Serializable person association for one UTC day."""

    day: date
    person_id: int
    person_name: str
    person_role: str | None


@dataclass(slots=True, frozen=True)
class DayTagLinkSnapshot:
    """Serializable tag association for one UTC day."""

    day: date
    tag_path: str
    tag_label: str


@dataclass(slots=True, frozen=True)
class DayMapPointSnapshot:
    """Serializable map point placement for one UTC day."""

    day: date
    item_type: str
    item_id: int
    timestamp: datetime
    label: str | None
    fallback_type: str
    fallback_identifier: str | None
    latitude: float
    longitude: float


@dataclass(slots=True, frozen=True)
class DayTimelineItemSnapshot:
    """Serializable read-model payload for a day-detail item."""

    item_type: str
    id: int
    timestamp: datetime
    type: str
    title: str | None
    summary: str | None
    external_id: str | None


@dataclass(slots=True, frozen=True)
class _FilterableTimelineItemSnapshot:
    """Serializable canonical item used for item-level persistent filtering."""

    day: date
    item_type: str
    item_id: int
    timestamp: datetime
    source_type: str
    display_label: str
    fallback_identifier: str | None
    latitude: float | None
    longitude: float | None


class DailyAggregateReadRepository:
    """Read derived daily aggregate rows for exploration projections."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_range(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> list[DailyAggregateReadSnapshot]:
        """Return overall aggregate rows in an inclusive date range."""

        statement = (
            select(DailyAggregate, DailyView)
            .join(DailyView, DailyView.id == DailyAggregate.daily_view_id)
            .where(
                DailyAggregate.date >= start_date,
                DailyAggregate.date <= end_date,
                DailyView.aggregate_scope == DAILY_AGGREGATE_SCOPE_OVERALL,
                DailyView.source_type.is_(None),
            )
            .order_by(DailyAggregate.date)
        )
        rows = self._session.execute(statement)
        return [
            _to_daily_aggregate_read_snapshot(aggregate=aggregate, daily_view=daily_view)
            for aggregate, daily_view in rows
        ]

    def list_range_for_view(
        self,
        *,
        start_date: date,
        end_date: date,
        view_id: str,
    ) -> list[DailyAggregateReadSnapshot]:
        """Return aggregate rows for one API-facing daily-view identifier."""

        statement = (
            select(DailyAggregate, DailyView)
            .join(DailyView, DailyView.id == DailyAggregate.daily_view_id)
            .where(
                DailyAggregate.date >= start_date,
                DailyAggregate.date <= end_date,
                *_build_daily_view_filters(view_id=view_id),
            )
            .order_by(DailyAggregate.date)
        )
        rows = self._session.execute(statement)
        return [
            _to_daily_aggregate_read_snapshot(aggregate=aggregate, daily_view=daily_view)
            for aggregate, daily_view in rows
        ]

    def list_source_type_range(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> list[DailyAggregateReadSnapshot]:
        """Return connector-scoped aggregate rows in an inclusive date range."""

        statement = (
            select(DailyAggregate, DailyView)
            .join(DailyView, DailyView.id == DailyAggregate.daily_view_id)
            .where(
                DailyAggregate.date >= start_date,
                DailyAggregate.date <= end_date,
                DailyView.aggregate_scope == DAILY_AGGREGATE_SCOPE_SOURCE_TYPE,
            )
            .order_by(DailyAggregate.date, DailyView.source_type)
        )
        rows = self._session.execute(statement)
        return [
            _to_daily_aggregate_read_snapshot(aggregate=aggregate, daily_view=daily_view)
            for aggregate, daily_view in rows
        ]

    def resolve_bounds(self) -> TimelineBoundsSnapshot | None:
        """Return aggregate-backed timeline bounds for exploration grid ranges."""

        min_date, max_date = self._session.execute(
            select(func.min(DailyAggregate.date), func.max(DailyAggregate.date))
            .join(DailyView, DailyView.id == DailyAggregate.daily_view_id)
            .where(
                DailyView.aggregate_scope == DAILY_AGGREGATE_SCOPE_OVERALL,
                DailyView.source_type.is_(None),
            )
        ).one()
        if min_date is None or max_date is None:
            return None

        return TimelineBoundsSnapshot(start_date=min_date, end_date=max_date)


class ExplorationReadRepository:
    """Read canonical and derived snapshots for exploration bootstrap."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_daily_views(self) -> list[DailyViewCatalogSnapshot]:
        """Return persisted daily-view metadata in a stable UI-facing order."""

        statement = select(DailyView).order_by(
            DailyView.aggregate_scope,
            DailyView.source_type,
            DailyView.id,
        )
        views = self._session.execute(statement).scalars()
        return [
            DailyViewCatalogSnapshot(
                view_id=_to_daily_view_catalog_id(view),
                label=view.label,
                description=view.description,
            )
            for view in views
        ]

    def list_filtered_day_aggregates(
        self,
        *,
        start_date: date,
        end_date: date,
        view_id: str,
        candidate_days: set[date],
        person_ids: tuple[int, ...],
        tag_paths: tuple[str, ...],
        base_aggregates_by_day: dict[date, DailyAggregateReadSnapshot],
    ) -> list[DailyAggregateReadSnapshot]:
        """Return canonical item-filtered day aggregates for candidate days only."""

        if not candidate_days:
            return []

        event_items = self._list_filterable_event_items(
            start_date=start_date,
            end_date=end_date,
            view_id=view_id,
            candidate_days=candidate_days,
        )
        asset_items = self._list_filterable_asset_items(
            start_date=start_date,
            end_date=end_date,
            view_id=view_id,
            candidate_days=candidate_days,
        )
        all_items = [*event_items, *asset_items]
        if not all_items:
            return []

        event_ids = [item.item_id for item in event_items]
        asset_ids = [item.item_id for item in asset_items]
        event_persons = self._list_event_person_links_by_item(event_ids=event_ids)
        asset_persons = self._list_asset_person_links_by_item(asset_ids=asset_ids)
        event_tags = self._list_event_tag_links_by_item(event_ids=event_ids)
        asset_tags = self._list_asset_tag_links_by_item(asset_ids=asset_ids)

        filtered_by_day: dict[date, list[_FilterableTimelineItemSnapshot]] = {}
        matched_persons: dict[tuple[str, int], list[tuple[int, str, str | None]]] = {}
        matched_tags: dict[tuple[str, int], list[tuple[str, str]]] = {}
        for item in all_items:
            item_key = (item.item_type, item.item_id)
            item_persons = (
                event_persons[item.item_id]
                if item.item_type == "event"
                else asset_persons[item.item_id]
            )
            item_tags = (
                event_tags[item.item_id]
                if item.item_type == "event"
                else asset_tags[item.item_id]
            )
            if person_ids and not set(person_ids).intersection(
                person_id for person_id, _name, _role in item_persons
            ):
                continue
            if tag_paths and not any(
                _tag_path_matches_selection(day_tag_path=item_tag_path, selected_tag_path=selected_tag_path)
                for item_tag_path, _label in item_tags
                for selected_tag_path in tag_paths
            ):
                continue
            filtered_by_day.setdefault(item.day, []).append(item)
            matched_persons[item_key] = item_persons
            matched_tags[item_key] = item_tags

        snapshots: list[DailyAggregateReadSnapshot] = []
        for current_day, items in sorted(filtered_by_day.items()):
            base_aggregate = base_aggregates_by_day.get(current_day)
            if base_aggregate is None:
                continue
            total_events = sum(1 for item in items if item.item_type == "event")
            media_count = sum(1 for item in items if item.item_type == "asset")
            person_summaries = _build_person_summary_from_items(
                items=items,
                persons_by_item=matched_persons,
            )
            tag_summaries = _build_tag_summary_from_items(
                items=items,
                tags_by_item=matched_tags,
            )
            location_summaries = _build_location_summary_from_items(items)
            snapshots.append(
                DailyAggregateReadSnapshot(
                    date=current_day,
                    total_events=total_events,
                    media_count=media_count,
                    activity_score=total_events + media_count,
                    color_value=base_aggregate.color_value,
                    title=base_aggregate.title,
                    aggregate_scope=base_aggregate.aggregate_scope,
                    source_type=base_aggregate.source_type,
                    tag_summary_json=tag_summaries,
                    person_summary_json=person_summaries,
                    location_summary_json=location_summaries,
                    metadata_json=dict(base_aggregate.metadata_json),
                )
            )

        return snapshots

    def list_event_days(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> list[DayActivityItemSnapshot]:
        """Return UTC day placement for canonical events in range."""

        statement = _apply_datetime_range(
            select(Event.id, Event.timestamp_start).order_by(
                Event.timestamp_start,
                Event.id,
            ),
            column=Event.timestamp_start,
            start_date=start_date,
            end_date=end_date,
        )
        rows = self._session.execute(statement)
        return [
            DayActivityItemSnapshot(id=event_id, day=timestamp.date())
            for event_id, timestamp in rows
        ]

    def list_asset_days(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> list[DayActivityItemSnapshot]:
        """Return UTC day placement for canonical assets in range."""

        statement = _apply_datetime_range(
            select(Asset.id, Asset.timestamp).order_by(
                Asset.timestamp,
                Asset.id,
            ),
            column=Asset.timestamp,
            start_date=start_date,
            end_date=end_date,
        )
        rows = self._session.execute(statement)
        return [
            DayActivityItemSnapshot(id=asset_id, day=timestamp.date())
            for asset_id, timestamp in rows
        ]

    def list_person_links(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> list[DayPersonLinkSnapshot]:
        """Return person links across events and assets in range."""

        return sorted(
            [
                *self._list_event_person_links(
                    start_date=start_date,
                    end_date=end_date,
                ),
                *self._list_asset_person_links(
                    start_date=start_date,
                    end_date=end_date,
                ),
            ],
            key=lambda snapshot: (
                snapshot.day,
                snapshot.person_name.casefold(),
                snapshot.person_id,
            ),
        )

    def list_tag_links(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> list[DayTagLinkSnapshot]:
        """Return tag links across events and assets in range."""

        return sorted(
            [
                *self._list_event_tag_links(
                    start_date=start_date,
                    end_date=end_date,
                ),
                *self._list_asset_tag_links(
                    start_date=start_date,
                    end_date=end_date,
                ),
            ],
            key=lambda snapshot: (snapshot.day, snapshot.tag_path, snapshot.tag_label),
        )

    def list_map_points(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> list[DayMapPointSnapshot]:
        """Return coordinate-bearing canonical items in range."""

        return sorted(
            [
                *self._list_event_map_points(
                    start_date=start_date,
                    end_date=end_date,
                ),
                *self._list_asset_map_points(
                    start_date=start_date,
                    end_date=end_date,
                ),
            ],
            key=lambda snapshot: (
                snapshot.day,
                snapshot.timestamp,
                snapshot.item_type,
                snapshot.item_id,
            ),
        )

    def _list_event_person_links(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> list[DayPersonLinkSnapshot]:
        """Return person associations linked through events."""

        statement = _apply_datetime_range(
            select(
                Event.timestamp_start,
                Person.id,
                Person.name,
                Person.metadata_json,
            )
            .join(EventPerson, EventPerson.event_id == Event.id)
            .join(Person, Person.id == EventPerson.person_id)
            .order_by(Event.timestamp_start, Person.name, Person.id),
            column=Event.timestamp_start,
            start_date=start_date,
            end_date=end_date,
        )
        rows = self._session.execute(statement)
        return [
            DayPersonLinkSnapshot(
                day=timestamp.date(),
                person_id=person_id,
                person_name=person_name,
                person_role=_extract_person_role(metadata_json),
            )
            for timestamp, person_id, person_name, metadata_json in rows
        ]

    def _list_event_person_links_by_item(
        self,
        *,
        event_ids: list[int],
    ) -> dict[int, list[tuple[int, str, str | None]]]:
        """Return event-linked people keyed by event identifier."""

        if not event_ids:
            return {}

        rows = self._session.execute(
            select(EventPerson.event_id, Person.id, Person.name, Person.metadata_json)
            .join(Person, Person.id == EventPerson.person_id)
            .where(EventPerson.event_id.in_(event_ids))
            .order_by(EventPerson.event_id, Person.name, Person.id)
        )
        links: dict[int, list[tuple[int, str, str | None]]] = {event_id: [] for event_id in event_ids}
        for event_id, person_id, person_name, metadata_json in rows:
            links.setdefault(event_id, []).append(
                (person_id, person_name, _extract_person_role(metadata_json))
            )
        return links

    def _list_asset_person_links(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> list[DayPersonLinkSnapshot]:
        """Return person associations linked through assets."""

        statement = _apply_datetime_range(
            select(
                Asset.timestamp,
                Person.id,
                Person.name,
                Person.metadata_json,
            )
            .join(AssetPerson, AssetPerson.asset_id == Asset.id)
            .join(Person, Person.id == AssetPerson.person_id)
            .order_by(Asset.timestamp, Person.name, Person.id),
            column=Asset.timestamp,
            start_date=start_date,
            end_date=end_date,
        )
        rows = self._session.execute(statement)
        return [
            DayPersonLinkSnapshot(
                day=timestamp.date(),
                person_id=person_id,
                person_name=person_name,
                person_role=_extract_person_role(metadata_json),
            )
            for timestamp, person_id, person_name, metadata_json in rows
        ]

    def _list_asset_person_links_by_item(
        self,
        *,
        asset_ids: list[int],
    ) -> dict[int, list[tuple[int, str, str | None]]]:
        """Return asset-linked people keyed by asset identifier."""

        if not asset_ids:
            return {}

        rows = self._session.execute(
            select(AssetPerson.asset_id, Person.id, Person.name, Person.metadata_json)
            .join(Person, Person.id == AssetPerson.person_id)
            .where(AssetPerson.asset_id.in_(asset_ids))
            .order_by(AssetPerson.asset_id, Person.name, Person.id)
        )
        links: dict[int, list[tuple[int, str, str | None]]] = {asset_id: [] for asset_id in asset_ids}
        for asset_id, person_id, person_name, metadata_json in rows:
            links.setdefault(asset_id, []).append(
                (person_id, person_name, _extract_person_role(metadata_json))
            )
        return links

    def _list_event_tag_links(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> list[DayTagLinkSnapshot]:
        """Return tag associations linked through events."""

        statement = _apply_datetime_range(
            select(Event.timestamp_start, Tag.path, Tag.label)
            .join(EventTag, EventTag.event_id == Event.id)
            .join(Tag, Tag.id == EventTag.tag_id)
            .where(Tag.path.is_not(None))
            .order_by(Event.timestamp_start, Tag.path, Tag.id),
            column=Event.timestamp_start,
            start_date=start_date,
            end_date=end_date,
        )
        rows = self._session.execute(statement)
        return [
            DayTagLinkSnapshot(
                day=timestamp.date(),
                tag_path=tag_path,
                tag_label=tag_label,
            )
            for timestamp, tag_path, tag_label in rows
        ]

    def _list_event_tag_links_by_item(
        self,
        *,
        event_ids: list[int],
    ) -> dict[int, list[tuple[str, str]]]:
        """Return event-linked tags keyed by event identifier."""

        if not event_ids:
            return {}

        rows = self._session.execute(
            select(EventTag.event_id, Tag.path, Tag.label)
            .join(Tag, Tag.id == EventTag.tag_id)
            .where(
                EventTag.event_id.in_(event_ids),
                Tag.path.is_not(None),
            )
            .order_by(EventTag.event_id, Tag.path, Tag.id)
        )
        links: dict[int, list[tuple[str, str]]] = {event_id: [] for event_id in event_ids}
        for event_id, tag_path, tag_label in rows:
            links.setdefault(event_id, []).append((tag_path, tag_label))
        return links

    def _list_asset_tag_links(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> list[DayTagLinkSnapshot]:
        """Return tag associations linked through assets."""

        statement = _apply_datetime_range(
            select(Asset.timestamp, Tag.path, Tag.label)
            .join(AssetTag, AssetTag.asset_id == Asset.id)
            .join(Tag, Tag.id == AssetTag.tag_id)
            .where(Tag.path.is_not(None))
            .order_by(Asset.timestamp, Tag.path, Tag.id),
            column=Asset.timestamp,
            start_date=start_date,
            end_date=end_date,
        )
        rows = self._session.execute(statement)
        return [
            DayTagLinkSnapshot(
                day=timestamp.date(),
                tag_path=tag_path,
                tag_label=tag_label,
            )
            for timestamp, tag_path, tag_label in rows
        ]

    def _list_asset_tag_links_by_item(
        self,
        *,
        asset_ids: list[int],
    ) -> dict[int, list[tuple[str, str]]]:
        """Return asset-linked tags keyed by asset identifier."""

        if not asset_ids:
            return {}

        rows = self._session.execute(
            select(AssetTag.asset_id, Tag.path, Tag.label)
            .join(Tag, Tag.id == AssetTag.tag_id)
            .where(
                AssetTag.asset_id.in_(asset_ids),
                Tag.path.is_not(None),
            )
            .order_by(AssetTag.asset_id, Tag.path, Tag.id)
        )
        links: dict[int, list[tuple[str, str]]] = {asset_id: [] for asset_id in asset_ids}
        for asset_id, tag_path, tag_label in rows:
            links.setdefault(asset_id, []).append((tag_path, tag_label))
        return links

    def _list_filterable_event_items(
        self,
        *,
        start_date: date,
        end_date: date,
        view_id: str,
        candidate_days: set[date],
    ) -> list[_FilterableTimelineItemSnapshot]:
        """Return canonical events eligible for item-level filter evaluation."""

        statement = _apply_datetime_range(
            select(
                Event.id,
                Event.timestamp_start,
                Source.type,
                Event.title,
                Event.latitude,
                Event.longitude,
            )
            .join(Source, Source.id == Event.source_id)
            .order_by(Event.timestamp_start, Event.id),
            column=Event.timestamp_start,
            start_date=start_date,
            end_date=end_date,
        )
        if view_id != "activity":
            statement = statement.where(Source.type == view_id)
        rows = self._session.execute(statement)
        return [
            _FilterableTimelineItemSnapshot(
                day=timestamp.date(),
                item_type="event",
                item_id=event_id,
                timestamp=timestamp,
                source_type=source_type,
                display_label=title,
                fallback_identifier=None,
                latitude=latitude,
                longitude=longitude,
            )
            for event_id, timestamp, source_type, title, latitude, longitude in rows
            if timestamp.date() in candidate_days
        ]

    def _list_filterable_asset_items(
        self,
        *,
        start_date: date,
        end_date: date,
        view_id: str,
        candidate_days: set[date],
    ) -> list[_FilterableTimelineItemSnapshot]:
        """Return canonical assets eligible for item-level filter evaluation."""

        statement = _apply_datetime_range(
            select(
                Asset.id,
                Asset.timestamp,
                Asset.media_type,
                Asset.external_id,
                Asset.summary,
                Asset.metadata_json,
                Asset.latitude,
                Asset.longitude,
            ).order_by(Asset.timestamp, Asset.id),
            column=Asset.timestamp,
            start_date=start_date,
            end_date=end_date,
        )
        if view_id != "activity":
            statement = statement.where(Asset.media_type == view_id)
        rows = self._session.execute(statement)
        return [
            _FilterableTimelineItemSnapshot(
                day=timestamp.date(),
                item_type="asset",
                item_id=asset_id,
                timestamp=timestamp,
                source_type=media_type,
                display_label=_resolve_asset_display_label(
                    summary=summary,
                    metadata_json=metadata_json,
                    external_id=external_id,
                    media_type=media_type,
                ),
                fallback_identifier=external_id,
                latitude=latitude,
                longitude=longitude,
            )
            for (
                asset_id,
                timestamp,
                media_type,
                external_id,
                summary,
                metadata_json,
                latitude,
                longitude,
            ) in rows
            if timestamp.date() in candidate_days
        ]

    def _list_event_map_points(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> list[DayMapPointSnapshot]:
        """Return coordinate-bearing canonical events in range."""

        statement = _apply_datetime_range(
            select(
                Event.id,
                Event.timestamp_start,
                Event.title,
                Event.type,
                Event.latitude,
                Event.longitude,
            )
            .where(
                Event.latitude.is_not(None),
                Event.longitude.is_not(None),
            )
            .order_by(Event.timestamp_start, Event.id),
            column=Event.timestamp_start,
            start_date=start_date,
            end_date=end_date,
        )
        rows = self._session.execute(statement)
        return [
            DayMapPointSnapshot(
                day=timestamp.date(),
                item_type="event",
                item_id=event_id,
                timestamp=timestamp,
                label=title,
                fallback_type=event_type,
                fallback_identifier=None,
                latitude=latitude,
                longitude=longitude,
            )
            for event_id, timestamp, title, event_type, latitude, longitude in rows
        ]

    def _list_asset_map_points(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> list[DayMapPointSnapshot]:
        """Return coordinate-bearing canonical assets in range."""

        statement = _apply_datetime_range(
            select(
                Asset.id,
                Asset.timestamp,
                Asset.media_type,
                Asset.external_id,
                Asset.metadata_json,
                Asset.latitude,
                Asset.longitude,
            )
            .where(
                Asset.latitude.is_not(None),
                Asset.longitude.is_not(None),
            )
            .order_by(Asset.timestamp, Asset.id),
            column=Asset.timestamp,
            start_date=start_date,
            end_date=end_date,
        )
        rows = self._session.execute(statement)
        return [
            DayMapPointSnapshot(
                day=timestamp.date(),
                item_type="asset",
                item_id=asset_id,
                timestamp=timestamp,
                label=_extract_asset_label(metadata_json),
                fallback_type=media_type,
                fallback_identifier=external_id,
                latitude=latitude,
                longitude=longitude,
            )
            for (
                asset_id,
                timestamp,
                media_type,
                external_id,
                metadata_json,
                latitude,
                longitude,
            ) in rows
        ]


class DayTimelineRepository:
    """Read canonical events and assets for a unified day view."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_day(self, *, day: date) -> list[DayTimelineItemSnapshot]:
        """Return a single UTC calendar day ordered across events and assets."""

        items = [*self._list_event_items(day=day), *self._list_asset_items(day=day)]
        return sorted(items, key=lambda item: (item.timestamp, item.item_type, item.id))

    def _list_event_items(self, *, day: date) -> list[DayTimelineItemSnapshot]:
        """Return read snapshots for canonical events on the given day."""

        statement = _apply_datetime_range(
            select(Event).order_by(Event.timestamp_start, Event.id),
            column=Event.timestamp_start,
            start_date=day,
            end_date=day,
        )
        events = self._session.execute(statement).scalars()
        return [
            DayTimelineItemSnapshot(
                item_type="event",
                id=event.id,
                timestamp=event.timestamp_start,
                type=event.type,
                title=event.title,
                summary=event.summary,
                external_id=None,
            )
            for event in events
        ]

    def _list_asset_items(self, *, day: date) -> list[DayTimelineItemSnapshot]:
        """Return read snapshots for canonical assets on the given day."""

        statement = _apply_datetime_range(
            select(Asset).order_by(Asset.timestamp, Asset.id),
            column=Asset.timestamp,
            start_date=day,
            end_date=day,
        )
        assets = self._session.execute(statement).scalars()
        return [
            DayTimelineItemSnapshot(
                item_type="asset",
                id=asset.id,
                timestamp=asset.timestamp,
                type=asset.media_type,
                title=None,
                summary=None,
                external_id=asset.external_id,
            )
            for asset in assets
        ]


def _to_daily_aggregate_read_snapshot(
    *,
    aggregate: DailyAggregate,
    daily_view: DailyView,
) -> DailyAggregateReadSnapshot:
    """Map an ORM row to a read-only derived aggregate snapshot."""

    return DailyAggregateReadSnapshot(
        date=aggregate.date,
        total_events=aggregate.total_events,
        media_count=aggregate.media_count,
        activity_score=aggregate.activity_score,
        color_value=aggregate.color_value,
        title=aggregate.title,
        aggregate_scope=daily_view.aggregate_scope,
        source_type=(
            daily_view.source_type
            if daily_view.source_type is not None
            else DAILY_AGGREGATE_OVERALL_SOURCE_TYPE
        ),
        tag_summary_json=list(aggregate.tag_summary_json),
        person_summary_json=list(aggregate.person_summary_json),
        location_summary_json=list(aggregate.location_summary_json),
        metadata_json=dict(daily_view.metadata_json),
    )


def _build_person_summary_from_items(
    items: list[_FilterableTimelineItemSnapshot],
    *,
    persons_by_item: dict[tuple[str, int], list[tuple[int, str, str | None]]],
) -> list[dict[str, Any]]:
    counter: dict[tuple[int, str, str | None], int] = {}
    for item in items:
        for person in persons_by_item.get((item.item_type, item.item_id), []):
            counter[person] = counter.get(person, 0) + 1
    return [
        {"person_id": person_id, "name": name, "role": role, "count": count}
        for (person_id, name, role), count in sorted(
            counter.items(),
            key=lambda item: (-item[1], item[0][1].casefold(), item[0][0]),
        )
    ]


def _build_tag_summary_from_items(
    items: list[_FilterableTimelineItemSnapshot],
    *,
    tags_by_item: dict[tuple[str, int], list[tuple[str, str]]],
) -> list[dict[str, Any]]:
    counter: dict[tuple[str, str], int] = {}
    for item in items:
        for tag in tags_by_item.get((item.item_type, item.item_id), []):
            counter[tag] = counter.get(tag, 0) + 1
    return [
        {"path": path, "label": label, "count": count}
        for (path, label), count in sorted(
            counter.items(),
            key=lambda item: (-item[1], item[0][0], item[0][1].casefold()),
        )
    ]


def _build_location_summary_from_items(
    items: list[_FilterableTimelineItemSnapshot],
) -> list[dict[str, Any]]:
    counter: dict[tuple[str, float, float], int] = {}
    for item in items:
        if item.latitude is None or item.longitude is None:
            continue
        key = (item.display_label, item.latitude, item.longitude)
        counter[key] = counter.get(key, 0) + 1
    return [
        {
            "label": label,
            "latitude": latitude,
            "longitude": longitude,
            "count": count,
        }
        for (label, latitude, longitude), count in sorted(
            counter.items(),
            key=lambda item: (-item[1], item[0][0].casefold(), item[0][1], item[0][2]),
        )
    ]


def _resolve_asset_display_label(
    *,
    summary: str | None,
    metadata_json: object,
    external_id: str,
    media_type: str,
) -> str:
    if isinstance(summary, str) and summary.strip():
        return summary.strip()

    extracted = _extract_asset_label(metadata_json)
    if extracted is not None:
        return extracted

    normalized_external_id = external_id.strip()
    if normalized_external_id:
        return normalized_external_id
    return media_type


def _tag_path_matches_selection(*, day_tag_path: str, selected_tag_path: str) -> bool:
    return (
        day_tag_path == selected_tag_path
        or day_tag_path.startswith(f"{selected_tag_path}/")
        or selected_tag_path.startswith(f"{day_tag_path}/")
    )


def _extract_person_role(metadata_json: object) -> str | None:
    """Extract a lightweight display role from person metadata."""

    if not isinstance(metadata_json, dict):
        return None

    role = metadata_json.get("role")
    return role if isinstance(role, str) and role else None


def _extract_asset_label(metadata_json: object) -> str | None:
    """Extract the first useful display label from asset metadata."""

    if not isinstance(metadata_json, dict):
        return None

    for key in ("label", "title", "filename", "original_filename"):
        value = metadata_json.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def _to_daily_view_catalog_id(view: DailyView) -> str:
    """Return the stable API identifier for one persisted daily view."""

    if view.aggregate_scope == DAILY_AGGREGATE_SCOPE_OVERALL:
        return "activity"

    if view.aggregate_scope == DAILY_AGGREGATE_SCOPE_SOURCE_TYPE:
        assert view.source_type is not None
        return view.source_type

    raise ValueError(f"unsupported daily view scope: {view.aggregate_scope}")


def _build_daily_view_filters(view_id: str) -> tuple[Any, ...]:
    """Return SQLAlchemy predicates for one API-facing daily-view identifier."""

    if view_id == "activity":
        return (
            DailyView.aggregate_scope == DAILY_AGGREGATE_SCOPE_OVERALL,
            DailyView.source_type.is_(None),
        )

    return (
        DailyView.aggregate_scope == DAILY_AGGREGATE_SCOPE_SOURCE_TYPE,
        DailyView.source_type == view_id,
    )
