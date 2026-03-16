"""Canonical SQLAlchemy mappings for PixelPast v0."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship

from pixelpast.persistence.base import Base
from pixelpast.persistence.types import UTCDateTime

DAILY_AGGREGATE_SCOPE_OVERALL = "overall"
DAILY_AGGREGATE_SCOPE_SOURCE_TYPE = "source_type"
DAILY_AGGREGATE_OVERALL_SOURCE_TYPE = "__all__"
JOB_RUN_TYPE_DERIVE = "derive"
JOB_RUN_TYPE_INGEST = "ingest"


def utc_now() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(UTC)


class Source(Base):
    """Represents an external or local source system."""

    __tablename__ = "source"
    __table_args__ = (
        UniqueConstraint("type", "name", name="uq_source_type_name"),
        UniqueConstraint("external_id", name="uq_source_external_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=utc_now,
        server_default=func.current_timestamp(),
    )


class JobRun(Base):
    """Tracks the execution of one ingest or derive job run."""

    __tablename__ = "import_run"
    __table_args__ = (
        CheckConstraint(
            "type IN ('ingest', 'derive')",
            name="ck_import_run_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    job: Mapped[str] = mapped_column(String(255), nullable=False)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    mode: Mapped[str] = mapped_column(String(50), nullable=False)
    phase: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(),
        nullable=True,
    )
    progress_json: Mapped[dict[str, Any] | None] = mapped_column(
        "progress",
        JSON,
        nullable=True,
    )


class Event(Base):
    """Represents a meaningful time-based occurrence."""

    __tablename__ = "event"
    __table_args__ = (
        Index("ix_event_timestamp_start", "timestamp_start"),
        Index("ix_event_source_id", "source_id"),
        Index("ix_event_type", "type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("source.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp_start: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    timestamp_end: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text(), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float(), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float(), nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    derived_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=utc_now,
        server_default=func.current_timestamp(),
    )


class Asset(Base):
    """Represents a time-located digital object."""

    __tablename__ = "asset"
    __table_args__ = (
        Index("ix_asset_timestamp", "timestamp"),
        UniqueConstraint("external_id", name="uq_asset_external_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(512), nullable=False)
    media_type: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text(), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float(), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float(), nullable=True)
    creator_person_id: Mapped[int | None] = mapped_column(
        ForeignKey("person.id"),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
    )


class DailyView(Base):
    """Catalog entry describing one reusable derived daily view."""

    __tablename__ = "daily_view"
    __table_args__ = (
        CheckConstraint(
            "aggregate_scope IN ('overall', 'source_type')",
            name="ck_daily_view_scope",
        ),
        CheckConstraint(
            "("
            "aggregate_scope = 'overall' AND source_type IS NULL"
            ") OR ("
            "aggregate_scope = 'source_type' AND source_type IS NOT NULL"
            ")",
            name="ck_daily_view_scope_source_type",
        ),
        UniqueConstraint(
            "aggregate_scope",
            "source_type",
            name="uq_daily_view_scope_source_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    aggregate_scope: Mapped[str] = mapped_column(String(50), nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text(), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )
    aggregates: Mapped[list["DailyAggregate"]] = relationship(
        back_populates="daily_view"
    )


class DailyAggregate(Base):
    """Stores per-day derived summaries for overall and connector-scoped views."""

    __tablename__ = "daily_aggregate"
    __table_args__ = (
        Index("ix_daily_aggregate_view_date", "daily_view_id", "date"),
    )

    date: Mapped[date] = mapped_column(Date(), primary_key=True)
    daily_view_id: Mapped[int] = mapped_column(
        ForeignKey("daily_view.id"),
        primary_key=True,
        nullable=False,
    )
    total_events: Mapped[int] = mapped_column(nullable=False, default=0)
    media_count: Mapped[int] = mapped_column(nullable=False, default=0)
    activity_score: Mapped[int] = mapped_column(nullable=False, default=0)
    tag_summary_json: Mapped[list[dict[str, Any]]] = mapped_column(
        "tag_summary",
        JSON,
        nullable=False,
        default=list,
    )
    person_summary_json: Mapped[list[dict[str, Any]]] = mapped_column(
        "person_summary",
        JSON,
        nullable=False,
        default=list,
    )
    location_summary_json: Mapped[list[dict[str, Any]]] = mapped_column(
        "location_summary",
        JSON,
        nullable=False,
        default=list,
    )
    daily_view: Mapped[DailyView] = relationship(
        back_populates="aggregates",
        lazy="joined",
    )

    @property
    def aggregate_scope(self) -> str:
        """Return the view scope through the normalized daily-view relationship."""

        return self.daily_view.aggregate_scope

    @property
    def source_type(self) -> str:
        """Return the legacy aggregate source identifier via the daily view."""

        if self.daily_view.source_type is None:
            return DAILY_AGGREGATE_OVERALL_SOURCE_TYPE
        return self.daily_view.source_type


class EventAsset(Base):
    """Associates events with assets."""

    __tablename__ = "event_asset"

    event_id: Mapped[int] = mapped_column(
        ForeignKey("event.id"),
        primary_key=True,
    )
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("asset.id"),
        primary_key=True,
    )
    link_type: Mapped[str] = mapped_column(String(50), nullable=False)


class Tag(Base):
    """Semantic annotation for events and assets."""

    __tablename__ = "tag"
    __table_args__ = (
        UniqueConstraint("path", name="uq_tag_path"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
    )


class EventTag(Base):
    """Associates events with tags."""

    __tablename__ = "event_tag"

    event_id: Mapped[int] = mapped_column(
        ForeignKey("event.id"),
        primary_key=True,
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tag.id"),
        primary_key=True,
    )


class AssetTag(Base):
    """Associates assets with tags."""

    __tablename__ = "asset_tag"

    asset_id: Mapped[int] = mapped_column(
        ForeignKey("asset.id"),
        primary_key=True,
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tag.id"),
        primary_key=True,
    )


class Person(Base):
    """Represents a known or inferred person."""

    __tablename__ = "person"
    __table_args__ = (
        UniqueConstraint("path", name="uq_person_path"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    aliases: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
    )


class EventPerson(Base):
    """Associates people with events."""

    __tablename__ = "event_person"

    event_id: Mapped[int] = mapped_column(
        ForeignKey("event.id"),
        primary_key=True,
    )
    person_id: Mapped[int] = mapped_column(
        ForeignKey("person.id"),
        primary_key=True,
    )


class AssetPerson(Base):
    """Associates people with assets."""

    __tablename__ = "asset_person"

    asset_id: Mapped[int] = mapped_column(
        ForeignKey("asset.id"),
        primary_key=True,
    )
    person_id: Mapped[int] = mapped_column(
        ForeignKey("person.id"),
        primary_key=True,
    )


class PersonGroup(Base):
    """Represents a named group of people."""

    __tablename__ = "person_group"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class PersonGroupMember(Base):
    """Associates people with person groups."""

    __tablename__ = "person_group_member"

    group_id: Mapped[int] = mapped_column(
        ForeignKey("person_group.id"),
        primary_key=True,
    )
    person_id: Mapped[int] = mapped_column(
        ForeignKey("person.id"),
        primary_key=True,
    )
