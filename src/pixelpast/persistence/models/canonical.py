"""Canonical SQLAlchemy mappings for PixelPast v0."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
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

from pixelpast.persistence.base import Base
from pixelpast.persistence.types import UTCDateTime


def utc_now() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(UTC)


class Source(Base):
    """Represents an external or local source system."""

    __tablename__ = "source"
    __table_args__ = (
        UniqueConstraint("type", "name", name="uq_source_type_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=utc_now,
        server_default=func.current_timestamp(),
    )


class ImportRun(Base):
    """Tracks the execution of an ingestion run."""

    __tablename__ = "import_run"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("source.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    mode: Mapped[str] = mapped_column(String(50), nullable=False)


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


class DailyAggregate(Base):
    """Stores derived per-day activity summaries for heatmap-style exploration."""

    __tablename__ = "daily_aggregate"

    date: Mapped[date] = mapped_column(Date(), primary_key=True)
    total_events: Mapped[int] = mapped_column(nullable=False, default=0)
    media_count: Mapped[int] = mapped_column(nullable=False, default=0)
    activity_score: Mapped[int] = mapped_column(nullable=False, default=0)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


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
