"""Repositories for canonical daily aggregate derivation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from pixelpast.persistence.models import (
    DAILY_AGGREGATE_OVERALL_SOURCE_TYPE,
    DAILY_AGGREGATE_SCOPE_OVERALL,
    Asset,
    AssetPerson,
    AssetTag,
    DailyAggregate,
    Event,
    EventPerson,
    EventTag,
    Person,
    Source,
    Tag,
)


@dataclass(slots=True, frozen=True)
class DailyAggregateSnapshot:
    """Serializable repository payload for a derived day summary."""

    date: date
    total_events: int
    media_count: int
    activity_score: int
    tag_summary_json: list[dict[str, Any]]
    person_summary_json: list[dict[str, Any]]
    location_summary_json: list[dict[str, Any]]
    metadata_json: dict[str, Any]
    aggregate_scope: str = DAILY_AGGREGATE_SCOPE_OVERALL
    source_type: str = DAILY_AGGREGATE_OVERALL_SOURCE_TYPE


@dataclass(slots=True, frozen=True)
class CanonicalEventAggregateInput:
    """Canonical event contribution to a UTC day/source-type aggregate."""

    day: date
    source_type: str
    event_type: str
    title: str
    latitude: float | None
    longitude: float | None


@dataclass(slots=True, frozen=True)
class CanonicalAssetAggregateInput:
    """Canonical asset contribution to a UTC day/source-type aggregate."""

    day: date
    source_type: str
    external_id: str
    media_type: str
    summary: str | None
    metadata_json: dict[str, Any] | None
    latitude: float | None
    longitude: float | None


@dataclass(slots=True, frozen=True)
class CanonicalTagAggregateInput:
    """Canonical tag contribution to a UTC day/source-type aggregate."""

    day: date
    source_type: str
    path: str
    label: str


@dataclass(slots=True, frozen=True)
class CanonicalPersonAggregateInput:
    """Canonical person contribution to a UTC day/source-type aggregate."""

    day: date
    source_type: str
    person_id: int
    name: str
    role: str | None


class CanonicalTimelineRepository:
    """Read canonical day-level contributions used to build derived summaries."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_event_inputs(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[CanonicalEventAggregateInput]:
        """Return canonical event contributions in the requested UTC range."""

        statement = _apply_datetime_range(
            select(
                Event.timestamp_start,
                Source.type,
                Event.type,
                Event.title,
                Event.latitude,
                Event.longitude,
            )
            .join(Source, Source.id == Event.source_id)
            .order_by(Event.timestamp_start, Source.type, Event.id),
            column=Event.timestamp_start,
            start_date=start_date,
            end_date=end_date,
        )
        rows = self._session.execute(statement)
        return [
            CanonicalEventAggregateInput(
                day=timestamp.date(),
                source_type=source_type,
                event_type=event_type,
                title=title,
                latitude=latitude,
                longitude=longitude,
            )
            for timestamp, source_type, event_type, title, latitude, longitude in rows
        ]

    def list_asset_inputs(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[CanonicalAssetAggregateInput]:
        """Return canonical asset contributions in the requested UTC range."""

        statement = _apply_datetime_range(
            select(
                Asset.timestamp,
                Asset.media_type,
                Asset.external_id,
                Asset.summary,
                Asset.metadata_json,
                Asset.latitude,
                Asset.longitude,
            ).order_by(Asset.timestamp, Asset.media_type, Asset.id),
            column=Asset.timestamp,
            start_date=start_date,
            end_date=end_date,
        )
        rows = self._session.execute(statement)
        return [
            CanonicalAssetAggregateInput(
                day=timestamp.date(),
                source_type=media_type,
                external_id=external_id,
                media_type=media_type,
                summary=summary,
                metadata_json=metadata_json,
                latitude=latitude,
                longitude=longitude,
            )
            for (
                timestamp,
                media_type,
                external_id,
                summary,
                metadata_json,
                latitude,
                longitude,
            ) in rows
        ]

    def list_event_tag_inputs(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[CanonicalTagAggregateInput]:
        """Return event-linked tags in the requested UTC range."""

        statement = _apply_datetime_range(
            select(
                Event.timestamp_start,
                Source.type,
                Tag.path,
                Tag.label,
            )
            .join(Source, Source.id == Event.source_id)
            .join(EventTag, EventTag.event_id == Event.id)
            .join(Tag, Tag.id == EventTag.tag_id)
            .where(Tag.path.is_not(None))
            .order_by(Event.timestamp_start, Source.type, Tag.path, Tag.id, Event.id),
            column=Event.timestamp_start,
            start_date=start_date,
            end_date=end_date,
        )
        rows = self._session.execute(statement)
        return [
            CanonicalTagAggregateInput(
                day=timestamp.date(),
                source_type=source_type,
                path=tag_path,
                label=tag_label,
            )
            for timestamp, source_type, tag_path, tag_label in rows
        ]

    def list_asset_tag_inputs(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[CanonicalTagAggregateInput]:
        """Return asset-linked tags in the requested UTC range."""

        statement = _apply_datetime_range(
            select(
                Asset.timestamp,
                Asset.media_type,
                Tag.path,
                Tag.label,
            )
            .join(AssetTag, AssetTag.asset_id == Asset.id)
            .join(Tag, Tag.id == AssetTag.tag_id)
            .where(Tag.path.is_not(None))
            .order_by(Asset.timestamp, Asset.media_type, Tag.path, Tag.id, Asset.id),
            column=Asset.timestamp,
            start_date=start_date,
            end_date=end_date,
        )
        rows = self._session.execute(statement)
        return [
            CanonicalTagAggregateInput(
                day=timestamp.date(),
                source_type=source_type,
                path=tag_path,
                label=tag_label,
            )
            for timestamp, source_type, tag_path, tag_label in rows
        ]

    def list_event_person_inputs(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[CanonicalPersonAggregateInput]:
        """Return event-linked people in the requested UTC range."""

        statement = _apply_datetime_range(
            select(
                Event.timestamp_start,
                Source.type,
                Person.id,
                Person.name,
                Person.metadata_json,
            )
            .join(Source, Source.id == Event.source_id)
            .join(EventPerson, EventPerson.event_id == Event.id)
            .join(Person, Person.id == EventPerson.person_id)
            .order_by(
                Event.timestamp_start,
                Source.type,
                Person.name,
                Person.id,
                Event.id,
            ),
            column=Event.timestamp_start,
            start_date=start_date,
            end_date=end_date,
        )
        rows = self._session.execute(statement)
        return [
            CanonicalPersonAggregateInput(
                day=timestamp.date(),
                source_type=source_type,
                person_id=person_id,
                name=person_name,
                role=_extract_person_role(metadata_json),
            )
            for timestamp, source_type, person_id, person_name, metadata_json in rows
        ]

    def list_asset_person_inputs(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[CanonicalPersonAggregateInput]:
        """Return asset-linked people in the requested UTC range."""

        statement = _apply_datetime_range(
            select(
                Asset.timestamp,
                Asset.media_type,
                Person.id,
                Person.name,
                Person.metadata_json,
            )
            .join(AssetPerson, AssetPerson.asset_id == Asset.id)
            .join(Person, Person.id == AssetPerson.person_id)
            .order_by(
                Asset.timestamp,
                Asset.media_type,
                Person.name,
                Person.id,
                Asset.id,
            ),
            column=Asset.timestamp,
            start_date=start_date,
            end_date=end_date,
        )
        rows = self._session.execute(statement)
        return [
            CanonicalPersonAggregateInput(
                day=timestamp.date(),
                source_type=source_type,
                person_id=person_id,
                name=person_name,
                role=_extract_person_role(metadata_json),
            )
            for timestamp, source_type, person_id, person_name, metadata_json in rows
        ]


class DailyAggregateRepository:
    """Persist derived daily aggregate rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def replace_all(self, *, aggregates: list[DailyAggregateSnapshot]) -> None:
        """Delete all existing aggregate rows and replace them atomically."""

        self._session.execute(delete(DailyAggregate))
        self._insert(aggregates)

    def replace_range(
        self,
        *,
        start_date: date,
        end_date: date,
        aggregates: list[DailyAggregateSnapshot],
    ) -> None:
        """Delete and replace aggregate rows for an inclusive date window."""

        self._session.execute(
            delete(DailyAggregate).where(
                DailyAggregate.date >= start_date,
                DailyAggregate.date <= end_date,
            )
        )
        self._insert(aggregates)

    def _insert(self, aggregates: list[DailyAggregateSnapshot]) -> None:
        """Insert repository snapshots as ORM rows."""

        if not aggregates:
            return

        self._session.add_all(
            DailyAggregate(
                date=aggregate.date,
                aggregate_scope=aggregate.aggregate_scope,
                source_type=aggregate.source_type,
                total_events=aggregate.total_events,
                media_count=aggregate.media_count,
                activity_score=aggregate.activity_score,
                tag_summary_json=list(aggregate.tag_summary_json),
                person_summary_json=list(aggregate.person_summary_json),
                location_summary_json=list(aggregate.location_summary_json),
                metadata_json=dict(aggregate.metadata_json),
            )
            for aggregate in aggregates
        )


def _apply_datetime_range(
    statement,
    *,
    column,
    start_date: date | None,
    end_date: date | None,
):
    """Apply an inclusive UTC date range to a timestamp column."""

    if start_date is not None:
        statement = statement.where(
            column >= datetime.combine(start_date, time.min, tzinfo=UTC)
        )

    if end_date is not None:
        statement = statement.where(
            column
            < datetime.combine(
                end_date + timedelta(days=1),
                time.min,
                tzinfo=UTC,
            )
        )

    return statement


def _extract_person_role(metadata_json: object) -> str | None:
    """Extract a lightweight display role from person metadata."""

    if not isinstance(metadata_json, dict):
        return None

    role = metadata_json.get("role")
    return role if isinstance(role, str) and role else None
