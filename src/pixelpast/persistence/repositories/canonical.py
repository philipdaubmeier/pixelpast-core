"""Canonical repositories for source state and operational job runs."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from pixelpast.persistence.asset_short_ids import (
    build_asset_short_id_candidate,
    generate_random_asset_short_id,
)
from pixelpast.persistence.models import (
    Asset,
    AssetPerson,
    AssetTag,
    Event,
    JobRun,
    Person,
    Source,
    Tag,
)


def utc_now() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(UTC)


class SourceRepository:
    """Repository for canonical source records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_type_and_name(self, *, source_type: str, name: str) -> Source | None:
        """Return the configured source matching a connector type and name."""

        statement = (
            select(Source)
            .where(Source.type == source_type, Source.name == name)
            .order_by(Source.id)
        )
        return self._session.execute(statement).scalars().first()

    def get_by_external_id(self, *, external_id: str) -> Source | None:
        """Return the configured source matching a stable external identifier."""

        statement = select(Source).where(Source.external_id == external_id)
        return self._session.execute(statement).scalar_one_or_none()

    def get_or_create(
        self,
        *,
        name: str,
        source_type: str,
        config: dict[str, Any],
    ) -> Source:
        """Return an existing source or create one for the connector."""

        source = self.get_by_type_and_name(source_type=source_type, name=name)
        if source is None:
            source = Source(
                name=name,
                type=source_type,
                external_id=None,
                config=dict(config),
            )
            self._session.add(source)
            self._session.flush()
            return source

        source.name = name
        source.config = dict(config)
        self._session.flush()
        return source

    def get_or_create_by_external_id(
        self,
        *,
        external_id: str,
        name: str,
        source_type: str,
        config: dict[str, Any],
    ) -> Source:
        """Return an existing source by external identity or create one."""

        return self.upsert_by_external_id(
            external_id=external_id,
            name=name,
            source_type=source_type,
            config=config,
        ).source

    def upsert_by_external_id(
        self,
        *,
        external_id: str,
        name: str,
        source_type: str,
        config: dict[str, Any],
    ) -> "SourceUpsertResult":
        """Insert or update one source by its stable external identity."""

        source = self.get_by_external_id(external_id=external_id)
        if source is None:
            source = Source(
                name=name,
                type=source_type,
                external_id=external_id,
                config=dict(config),
            )
            self._session.add(source)
            self._session.flush()
            return SourceUpsertResult(source=source, status="inserted")

        next_config = dict(config)
        changed = any(
            [
                source.name != name,
                source.type != source_type,
                source.external_id != external_id,
                source.config != next_config,
            ]
        )
        source.name = name
        source.type = source_type
        source.external_id = external_id
        source.config = next_config
        self._session.flush()
        return SourceUpsertResult(
            source=source,
            status="updated" if changed else "unchanged",
        )


class SourceUpsertResult:
    """Represents the core-field upsert outcome for one source."""

    __slots__ = ("source", "status")

    def __init__(self, *, source: Source, status: str) -> None:
        self.source = source
        self.status = status


class JobRunRepository:
    """Repository for shared ingest/derive job run tracking."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        job_type: str,
        job: str,
        mode: str,
        status: str = "running",
        started_at: datetime | None = None,
        phase: str | None = None,
        progress_json: dict[str, Any] | None = None,
    ) -> JobRun:
        """Create and persist a running job record."""

        job_run = JobRun(
            type=job_type,
            job=job,
            started_at=started_at or utc_now(),
            finished_at=None,
            status=status,
            mode=mode,
            phase=phase,
            last_heartbeat_at=None,
            progress_json=(
                dict(progress_json) if progress_json is not None else None
            ),
        )
        self._session.add(job_run)
        self._session.flush()
        return job_run

    def get_by_id(self, *, run_id: int) -> JobRun | None:
        """Return a job run by identifier."""

        statement = select(JobRun).where(JobRun.id == run_id)
        return self._session.execute(statement).scalar_one_or_none()

    def mark_finished(
        self,
        job_run: JobRun,
        *,
        status: str,
        finished_at: datetime | None = None,
        phase: str | None = None,
        last_heartbeat_at: datetime | None = None,
        progress_json: dict[str, Any] | None = None,
    ) -> JobRun:
        """Mark a job run as finished with a terminal status."""

        job_run.status = status
        job_run.finished_at = finished_at or utc_now()
        job_run.phase = phase
        job_run.last_heartbeat_at = last_heartbeat_at or job_run.last_heartbeat_at
        if progress_json is not None:
            job_run.progress_json = dict(progress_json)
        self._session.flush()
        return job_run

    def update_progress(
        self,
        *,
        run_id: int,
        phase: str,
        progress_json: dict[str, Any],
        last_heartbeat_at: datetime | None = None,
        status: str | None = None,
    ) -> JobRun | None:
        """Persist a non-terminal progress heartbeat for a running job."""

        job_run = self.get_by_id(run_id=run_id)
        if job_run is None:
            return None

        job_run.phase = phase
        job_run.progress_json = dict(progress_json)
        job_run.last_heartbeat_at = last_heartbeat_at or utc_now()
        if status is not None:
            job_run.status = status
        self._session.flush()
        return job_run

    def mark_finished_by_id(
        self,
        *,
        run_id: int,
        status: str,
        finished_at: datetime | None = None,
        phase: str | None = None,
        last_heartbeat_at: datetime | None = None,
        progress_json: dict[str, Any] | None = None,
    ) -> JobRun | None:
        """Mark a job run as finished when only the identifier is available."""

        job_run = self.get_by_id(run_id=run_id)
        if job_run is None:
            return None
        return self.mark_finished(
            job_run,
            status=status,
            finished_at=finished_at,
            phase=phase,
            last_heartbeat_at=last_heartbeat_at,
            progress_json=progress_json,
        )


class AssetUpsertResult:
    """Represents the core-field upsert outcome for one asset."""

    __slots__ = ("asset", "status")

    def __init__(self, *, asset: Asset, status: str) -> None:
        self.asset = asset
        self.status = status


class AssetRepository:
    """Repository for canonical asset upserts."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_source_and_external_id(
        self,
        *,
        source_id: int,
        external_id: str,
    ) -> Asset | None:
        """Return an asset identified by its source-scoped stable key."""

        statement = select(Asset).where(
            Asset.source_id == source_id,
            Asset.external_id == external_id,
        )
        return self._session.execute(statement).scalar_one_or_none()

    def get_by_short_id(self, *, short_id: str) -> Asset | None:
        """Return an asset by its stable public short identifier."""

        statement = select(Asset).where(Asset.short_id == short_id)
        return self._session.execute(statement).scalar_one_or_none()

    def list_external_ids_under_prefix(
        self,
        *,
        source_id: int,
        external_id_prefix: str,
    ) -> list[str]:
        """Return external identifiers for one source and source path prefix."""

        normalized_prefix = external_id_prefix.rstrip("/") + "/"
        statement = (
            select(Asset.external_id)
            .where(
                Asset.source_id == source_id,
                Asset.external_id.like(f"{normalized_prefix}%"),
            )
            .order_by(Asset.external_id)
        )
        return list(self._session.execute(statement).scalars())

    def get_tag_ids(self, *, asset_id: int) -> list[int]:
        """Return deterministic tag identifiers currently linked to an asset."""

        statement = (
            select(AssetTag.tag_id)
            .where(AssetTag.asset_id == asset_id)
            .order_by(AssetTag.tag_id)
        )
        return list(self._session.execute(statement).scalars())

    def get_person_ids(self, *, asset_id: int) -> list[int]:
        """Return deterministic person identifiers currently linked to an asset."""

        statement = (
            select(AssetPerson.person_id)
            .where(AssetPerson.asset_id == asset_id)
            .order_by(AssetPerson.person_id)
        )
        return list(self._session.execute(statement).scalars())

    def upsert(
        self,
        *,
        short_id: str | None = None,
        source_id: int,
        external_id: str,
        media_type: str,
        timestamp: datetime,
        summary: str | None,
        latitude: float | None,
        longitude: float | None,
        creator_person_id: int | None,
        metadata_json: dict[str, Any] | None,
    ) -> AssetUpsertResult:
        """Insert or update an asset by external identifier."""

        asset = self.get_by_source_and_external_id(
            source_id=source_id,
            external_id=external_id,
        )
        if asset is None:
            return self._insert_asset_with_short_id_retries(
                short_id=short_id,
                source_id=source_id,
                external_id=external_id,
                media_type=media_type,
                timestamp=timestamp,
                summary=summary,
                latitude=latitude,
                longitude=longitude,
                creator_person_id=creator_person_id,
                metadata_json=metadata_json,
            )

        next_metadata = dict(metadata_json) if metadata_json is not None else None
        changed = any(
            [
                asset.source_id != source_id,
                asset.media_type != media_type,
                asset.timestamp != timestamp,
                asset.summary != summary,
                asset.latitude != latitude,
                asset.longitude != longitude,
                asset.creator_person_id != creator_person_id,
                asset.metadata_json != next_metadata,
            ]
        )
        short_id_backfilled = False
        if changed:
            asset.source_id = source_id
            asset.media_type = media_type
            asset.timestamp = timestamp
            asset.summary = summary
            asset.latitude = latitude
            asset.longitude = longitude
            asset.creator_person_id = creator_person_id
            asset.metadata_json = next_metadata
        elif asset.short_id is None:
            asset.short_id = short_id or self._allocate_short_id()
            short_id_backfilled = True
        self._session.flush()
        return AssetUpsertResult(
            asset=asset,
            status="updated" if changed or short_id_backfilled else "unchanged",
        )

    def _allocate_short_id(self) -> str:
        """Allocate a unique public short id for a new canonical asset."""

        for attempt in range(32):
            candidate = build_asset_short_id_candidate(
                seed=generate_random_asset_short_id(),
                attempt=attempt,
            )
            if self.get_by_short_id(short_id=candidate) is None:
                return candidate

        raise RuntimeError("Could not allocate a unique asset short id.")

    def _insert_asset_with_short_id_retries(
        self,
        *,
        short_id: str | None,
        source_id: int,
        external_id: str,
        media_type: str,
        timestamp: datetime,
        summary: str | None,
        latitude: float | None,
        longitude: float | None,
        creator_person_id: int | None,
        metadata_json: dict[str, Any] | None,
    ) -> AssetUpsertResult:
        next_metadata = dict(metadata_json) if metadata_json is not None else None

        for _ in range(32):
            candidate_short_id = short_id or self._allocate_short_id()
            if (
                short_id is None
                and self.get_by_short_id(short_id=candidate_short_id) is not None
            ):
                continue

            asset = Asset(
                short_id=candidate_short_id,
                source_id=source_id,
                external_id=external_id,
                media_type=media_type,
                timestamp=timestamp,
                summary=summary,
                latitude=latitude,
                longitude=longitude,
                creator_person_id=creator_person_id,
                metadata_json=next_metadata,
            )
            self._session.add(asset)
            self._session.flush()
            return AssetUpsertResult(asset=asset, status="inserted")

        raise RuntimeError("Could not allocate a unique asset short id.")

    def replace_tag_links(self, *, asset_id: int, tag_ids: Iterable[int]) -> bool:
        """Replace all asset-tag links with the provided deterministic set."""

        unique_tag_ids = sorted(set(tag_ids))
        if self.get_tag_ids(asset_id=asset_id) == unique_tag_ids:
            return False

        self._session.execute(delete(AssetTag).where(AssetTag.asset_id == asset_id))
        self._session.add_all(
            [AssetTag(asset_id=asset_id, tag_id=tag_id) for tag_id in unique_tag_ids]
        )
        self._session.flush()
        return True

    def replace_person_links(
        self,
        *,
        asset_id: int,
        person_ids: Iterable[int],
    ) -> bool:
        """Replace all asset-person links with the provided deterministic set."""

        unique_person_ids = sorted(set(person_ids))
        if self.get_person_ids(asset_id=asset_id) == unique_person_ids:
            return False

        self._session.execute(
            delete(AssetPerson).where(AssetPerson.asset_id == asset_id)
        )
        self._session.add_all(
            [
                AssetPerson(asset_id=asset_id, person_id=person_id)
                for person_id in unique_person_ids
            ]
        )
        self._session.flush()
        return True


class EventReplaceResult:
    """Represents the source-scoped replacement outcome for one event set."""

    __slots__ = (
        "persisted_event_count",
        "status",
        "inserted_event_count",
        "updated_event_count",
        "unchanged_event_count",
        "missing_from_source_count",
    )

    def __init__(
        self,
        *,
        persisted_event_count: int,
        status: str,
        inserted_event_count: int = 0,
        updated_event_count: int = 0,
        unchanged_event_count: int = 0,
        missing_from_source_count: int = 0,
    ) -> None:
        self.persisted_event_count = persisted_event_count
        self.status = status
        self.inserted_event_count = inserted_event_count
        self.updated_event_count = updated_event_count
        self.unchanged_event_count = unchanged_event_count
        self.missing_from_source_count = missing_from_source_count


class EventRepository:
    """Repository for source-scoped canonical event replacement."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_by_source_id(self, *, source_id: int) -> list[Event]:
        """Return deterministic persisted events for one canonical source."""

        statement = (
            select(Event)
            .where(Event.source_id == source_id)
            .order_by(Event.timestamp_start, Event.timestamp_end, Event.id)
        )
        return list(self._session.execute(statement).scalars())

    def replace_for_source(
        self,
        *,
        source_id: int,
        events: Sequence[dict[str, Any]],
    ) -> EventReplaceResult:
        """Reconcile one source's events against the next canonical payload."""

        persisted_events = self.list_by_source_id(source_id=source_id)
        existing_signatures = sorted(
            _serialize_event_signature_from_model(event) for event in persisted_events
        )
        next_signatures = sorted(
            _serialize_event_signature_from_payload(source_id=source_id, event=event)
            for event in events
        )
        if existing_signatures == next_signatures:
            return EventReplaceResult(
                persisted_event_count=len(events),
                status="unchanged",
                unchanged_event_count=len(events),
            )

        existing_by_identity = _build_unique_event_identity_map_from_models(
            persisted_events
        )
        next_by_identity = _build_unique_event_identity_map_from_payloads(events)
        if existing_by_identity is None or next_by_identity is None:
            return self._replace_for_source_fallback(
                source_id=source_id,
                persisted_events=persisted_events,
                events=events,
            )

        inserted_event_count = 0
        updated_event_count = 0
        unchanged_event_count = 0
        missing_from_source_count = 0

        existing_identities = set(existing_by_identity)
        next_identities = set(next_by_identity)

        for identity in sorted(existing_identities - next_identities):
            self._session.delete(existing_by_identity[identity])
            missing_from_source_count += 1

        for identity in sorted(next_identities - existing_identities):
            self._session.add(
                _build_event_model(source_id=source_id, event=next_by_identity[identity])
            )
            inserted_event_count += 1

        for identity in sorted(existing_identities & next_identities):
            persisted_event = existing_by_identity[identity]
            next_event = next_by_identity[identity]
            existing_signature = _serialize_event_signature_from_model(persisted_event)
            next_signature = _serialize_event_signature_from_payload(
                source_id=source_id,
                event=next_event,
            )
            if existing_signature == next_signature:
                unchanged_event_count += 1
                continue
            _apply_event_payload_to_model(event_model=persisted_event, event=next_event)
            updated_event_count += 1

        self._session.flush()
        return EventReplaceResult(
            persisted_event_count=len(events),
            status=_resolve_event_replace_status(
                inserted_event_count=inserted_event_count,
                updated_event_count=updated_event_count,
                unchanged_event_count=unchanged_event_count,
            ),
            inserted_event_count=inserted_event_count,
            updated_event_count=updated_event_count,
            unchanged_event_count=unchanged_event_count,
            missing_from_source_count=missing_from_source_count,
        )

    def count_missing_from_source(
        self,
        *,
        source_id: int,
        events: Sequence[dict[str, Any]],
    ) -> int:
        """Return how many persisted source events are absent from the next payload."""

        existing_by_identity = _build_unique_event_identity_map_from_models(
            self.list_by_source_id(source_id=source_id)
        )
        next_by_identity = _build_unique_event_identity_map_from_payloads(events)
        if existing_by_identity is None or next_by_identity is None:
            return 0
        return len(set(existing_by_identity) - set(next_by_identity))

    def _replace_for_source_fallback(
        self,
        *,
        source_id: int,
        persisted_events: Sequence[Event],
        events: Sequence[dict[str, Any]],
    ) -> EventReplaceResult:
        self._session.execute(delete(Event).where(Event.source_id == source_id))
        self._session.add_all(
            [_build_event_model(source_id=source_id, event=event) for event in events]
        )
        self._session.flush()
        return EventReplaceResult(
            persisted_event_count=len(events),
            status="inserted" if not persisted_events else "updated",
            inserted_event_count=(len(events) if not persisted_events else 0),
            updated_event_count=(len(events) if persisted_events else 0),
            unchanged_event_count=0,
            missing_from_source_count=0,
        )

class TagRepository:
    """Repository for canonical tag creation and lookup."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_path(self, *, path: str) -> Tag | None:
        """Return a tag by its normalized canonical path."""

        statement = select(Tag).where(Tag.path == path)
        return self._session.execute(statement).scalar_one_or_none()

    def get_or_create(
        self,
        *,
        path: str,
        metadata_json: dict[str, Any] | None = None,
    ) -> Tag:
        """Return an existing tag or create one from a canonical path."""

        tag = self.get_by_path(path=path)
        label = path.rsplit("|", 1)[-1]
        if tag is None:
            tag = Tag(
                label=label,
                path=path,
                metadata_json=(
                    dict(metadata_json) if metadata_json is not None else None
                ),
            )
            self._session.add(tag)
            self._session.flush()
            return tag

        tag.label = label
        if metadata_json is not None:
            tag.metadata_json = dict(metadata_json)
        self._session.flush()
        return tag


class PersonRepository:
    """Repository for canonical person creation and lookup."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_path(self, *, path: str) -> Person | None:
        """Return a person by canonical path when available."""

        statement = select(Person).where(Person.path == path)
        return self._session.execute(statement).scalar_one_or_none()

    def get_by_name(self, *, name: str) -> Person | None:
        """Return the first person matching a canonical display name."""

        statement = select(Person).where(Person.name == name).order_by(Person.id)
        return self._session.execute(statement).scalars().first()

    def get_or_create(
        self,
        *,
        name: str,
        path: str | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> Person:
        """Return a canonical person, preferring path-based identity when present."""

        person = None
        if path is not None:
            person = self.get_by_path(path=path)
        if person is None:
            person = self.get_by_name(name=name)

        if person is None:
            person = Person(
                name=name,
                path=path,
                metadata_json=(
                    dict(metadata_json) if metadata_json is not None else None
                ),
            )
            self._session.add(person)
            self._session.flush()
            return person

        person.name = name
        if person.path is None and path is not None:
            person.path = path
        if metadata_json is not None:
            person.metadata_json = dict(metadata_json)
        self._session.flush()
        return person


def _serialize_event_signature_from_model(event: Event) -> str:
    return json.dumps(
        {
            "source_id": event.source_id,
            "type": event.type,
            "timestamp_start": event.timestamp_start.isoformat(),
            "timestamp_end": (
                event.timestamp_end.isoformat()
                if event.timestamp_end is not None
                else None
            ),
            "title": event.title,
            "summary": event.summary,
            "latitude": event.latitude,
            "longitude": event.longitude,
            "raw_payload": event.raw_payload,
            "derived_payload": event.derived_payload,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _serialize_event_signature_from_payload(
    *,
    source_id: int,
    event: dict[str, Any],
) -> str:
    timestamp_end = event["timestamp_end"]
    return json.dumps(
        {
            "source_id": source_id,
            "type": event["type"],
            "timestamp_start": event["timestamp_start"].isoformat(),
            "timestamp_end": (
                timestamp_end.isoformat() if timestamp_end is not None else None
            ),
            "title": str(event.get("title") or ""),
            "summary": event["summary"],
            "latitude": event["latitude"],
            "longitude": event["longitude"],
            "raw_payload": dict(event["raw_payload"]),
            "derived_payload": dict(event["derived_payload"]),
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _build_event_model(*, source_id: int, event: dict[str, Any]) -> Event:
    return Event(
        source_id=source_id,
        type=str(event["type"]),
        timestamp_start=event["timestamp_start"],
        timestamp_end=event["timestamp_end"],
        title=str(event.get("title") or ""),
        summary=event["summary"],
        latitude=event["latitude"],
        longitude=event["longitude"],
        raw_payload=dict(event["raw_payload"]),
        derived_payload=dict(event["derived_payload"]),
    )


def _apply_event_payload_to_model(
    *,
    event_model: Event,
    event: dict[str, Any],
) -> None:
    event_model.type = str(event["type"])
    event_model.timestamp_start = event["timestamp_start"]
    event_model.timestamp_end = event["timestamp_end"]
    event_model.title = str(event.get("title") or "")
    event_model.summary = event["summary"]
    event_model.latitude = event["latitude"]
    event_model.longitude = event["longitude"]
    event_model.raw_payload = dict(event["raw_payload"])
    event_model.derived_payload = dict(event["derived_payload"])


def _build_unique_event_identity_map_from_models(
    events: Sequence[Event],
) -> dict[str, Event] | None:
    identities = [_event_identity_from_model(event) for event in events]
    if any(identity is None for identity in identities):
        return None
    keys = [identity for identity in identities if identity is not None]
    if len(keys) != len(set(keys)):
        return None
    return {
        identity: event
        for identity, event in zip(keys, events, strict=True)
    }


def _build_unique_event_identity_map_from_payloads(
    events: Sequence[dict[str, Any]],
) -> dict[str, dict[str, Any]] | None:
    identities = [_event_identity_from_payload(event) for event in events]
    if any(identity is None for identity in identities):
        return None
    keys = [identity for identity in identities if identity is not None]
    if len(keys) != len(set(keys)):
        return None
    return {
        identity: event
        for identity, event in zip(keys, events, strict=True)
    }


def _event_identity_from_model(event: Event) -> str | None:
    raw_payload = event.raw_payload if isinstance(event.raw_payload, dict) else {}
    external_event_id = raw_payload.get("external_event_id")
    if isinstance(external_event_id, str) and external_event_id:
        return f"external_event_id:{external_event_id}"
    uid = _event_uid_from_model(event)
    if uid is None:
        return None
    timestamp_end = (
        event.timestamp_end.isoformat() if event.timestamp_end is not None else "none"
    )
    return (
        f"uid:{uid}|dtstart:{event.timestamp_start.isoformat()}|dtend:{timestamp_end}"
    )


def _event_identity_from_payload(event: dict[str, Any]) -> str | None:
    external_event_id = event.get("external_event_id")
    if isinstance(external_event_id, str) and external_event_id:
        return f"external_event_id:{external_event_id}"
    uid = _event_uid_from_payload(event)
    if uid is None:
        return None
    timestamp_end = event["timestamp_end"]
    return (
        "uid:"
        f"{uid}|dtstart:{event['timestamp_start'].isoformat()}|dtend:"
        f"{timestamp_end.isoformat() if timestamp_end is not None else 'none'}"
    )


def _event_uid_from_model(event: Event) -> str | None:
    if isinstance(event.raw_payload, dict):
        uid = event.raw_payload.get("uid")
        if isinstance(uid, str) and uid:
            return uid
    return None


def _event_uid_from_payload(event: dict[str, Any]) -> str | None:
    external_event_id = event.get("external_event_id")
    if isinstance(external_event_id, str) and external_event_id:
        return external_event_id
    raw_payload = event.get("raw_payload")
    if isinstance(raw_payload, dict):
        uid = raw_payload.get("uid")
        if isinstance(uid, str) and uid:
            return uid
    return None


def _resolve_event_replace_status(
    *,
    inserted_event_count: int,
    updated_event_count: int,
    unchanged_event_count: int,
) -> str:
    if inserted_event_count and not updated_event_count and not unchanged_event_count:
        return "inserted"
    if inserted_event_count or updated_event_count:
        return "updated"
    return "unchanged"
