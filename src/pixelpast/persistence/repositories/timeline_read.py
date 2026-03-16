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
        aggregate_scope=daily_view.aggregate_scope,
        source_type=(
            daily_view.source_type
            if daily_view.source_type is not None
            else DAILY_AGGREGATE_OVERALL_SOURCE_TYPE
        ),
        tag_summary_json=list(aggregate.tag_summary_json),
        person_summary_json=list(aggregate.person_summary_json),
        location_summary_json=list(aggregate.location_summary_json),
        metadata_json=dict(aggregate.metadata_json),
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
