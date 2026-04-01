"""Shared narrow helpers for repeated ingestion persister mechanics."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any, Protocol

from pixelpast.persistence.repositories import (
    AssetRepository,
    AssetUpsertResult,
    EventReplaceResult,
    EventRepository,
    PersonRepository,
    SourceRepository,
    TagRepository,
)
from pixelpast.shared.persistence_outcome_summary import PersistenceOutcomeSummary


class AssetPersonLike(Protocol):
    """Structural contract for asset-linked person candidates."""

    name: str
    path: str | None


class AssetCandidateLike(Protocol):
    """Structural contract for canonical asset candidates."""

    external_id: str
    media_type: str
    timestamp: datetime
    summary: str | None
    latitude: float | None
    longitude: float | None
    creator_name: str | None
    tag_paths: Sequence[str]
    asset_tag_paths: Sequence[str]
    persons: Sequence[AssetPersonLike]
    metadata_json: dict[str, Any] | None


class SourceCandidateLike(Protocol):
    """Structural contract for canonical source candidates."""

    type: str
    name: str | None
    external_id: str | None
    config_json: dict[str, Any] | None


def persist_asset_candidate(
    *,
    source_id: int,
    asset_repository: AssetRepository,
    tag_repository: TagRepository,
    person_repository: PersonRepository,
    asset: AssetCandidateLike,
    folder_id: int | None = None,
) -> str:
    """Persist one asset candidate with shared link replacement mechanics."""

    creator_person_id = _resolve_creator_person_id(
        creator_name=asset.creator_name,
        person_repository=person_repository,
    )
    upsert_result = asset_repository.upsert(
        source_id=source_id,
        external_id=asset.external_id,
        media_type=asset.media_type,
        timestamp=asset.timestamp,
        summary=asset.summary,
        latitude=asset.latitude,
        longitude=asset.longitude,
        folder_id=folder_id,
        creator_person_id=creator_person_id,
        metadata_json=asset.metadata_json,
    )
    tags_changed = replace_asset_tag_links(
        asset_repository=asset_repository,
        tag_repository=tag_repository,
        asset_id=upsert_result.asset.id,
        tag_paths=asset.tag_paths,
        asset_tag_paths=asset.asset_tag_paths,
    )
    people_changed = replace_asset_person_links(
        asset_repository=asset_repository,
        person_repository=person_repository,
        asset_id=upsert_result.asset.id,
        persons=asset.persons,
    )
    return resolve_asset_persistence_outcome(
        upsert_result=upsert_result,
        tags_changed=tags_changed,
        people_changed=people_changed,
    )


def replace_asset_tag_links(
    *,
    asset_repository: AssetRepository,
    tag_repository: TagRepository,
    asset_id: int,
    tag_paths: Sequence[str],
    asset_tag_paths: Sequence[str],
) -> bool:
    """Create canonical tags as needed and replace the linked asset subset."""

    persisted_tags = {
        path: tag_repository.get_or_create(path=path)
        for path in tag_paths
    }
    return asset_repository.replace_tag_links(
        asset_id=asset_id,
        tag_ids=[
            persisted_tags[path].id
            for path in asset_tag_paths
            if path in persisted_tags
        ],
    )


def replace_asset_person_links(
    *,
    asset_repository: AssetRepository,
    person_repository: PersonRepository,
    asset_id: int,
    persons: Sequence[AssetPersonLike],
) -> bool:
    """Create canonical people as needed and replace asset-person links."""

    persisted_people = [
        person_repository.get_or_create(name=person.name, path=person.path)
        for person in persons
    ]
    return asset_repository.replace_person_links(
        asset_id=asset_id,
        person_ids=[person.id for person in persisted_people],
    )


def resolve_asset_persistence_outcome(
    *,
    upsert_result: AssetUpsertResult,
    tags_changed: bool,
    people_changed: bool,
) -> str:
    """Resolve the deterministic persistence outcome for one canonical asset."""

    if upsert_result.status == "inserted":
        return "inserted"
    if upsert_result.status == "updated" or tags_changed or people_changed:
        return "updated"
    return "unchanged"


def upsert_required_source(
    *,
    source_repository: SourceRepository,
    source: SourceCandidateLike,
    default_name: str,
    missing_external_id_message: str,
) -> int:
    """Upsert one source that must expose a stable external identity."""

    source_result = source_repository.upsert_by_external_id(
        external_id=require_source_external_id(
            source_external_id=source.external_id,
            missing_external_id_message=missing_external_id_message,
        ),
        name=source.name or source.external_id or default_name,
        source_type=source.type,
        config=source.config_json or {},
    )
    return source_result.source.id


def count_missing_events_for_source(
    *,
    source_repository: SourceRepository,
    event_repository: EventRepository,
    source: SourceCandidateLike,
    event_payloads: Sequence[dict[str, Any]],
    missing_external_id_message: str,
) -> int:
    """Preview source-scoped missing events for one replacement candidate."""

    source_external_id = require_source_external_id(
        source_external_id=source.external_id,
        missing_external_id_message=missing_external_id_message,
    )
    persisted_source = source_repository.get_by_external_id(
        external_id=source_external_id
    )
    if persisted_source is None:
        return 0
    return event_repository.count_missing_from_source(
        source_id=persisted_source.id,
        events=event_payloads,
    )


def replace_events_for_source(
    *,
    event_repository: EventRepository,
    source_id: int,
    event_payloads: Sequence[dict[str, Any]],
) -> EventReplaceResult:
    """Persist one canonical source-scoped replacement event set."""

    return event_repository.replace_for_source(
        source_id=source_id,
        events=event_payloads,
    )


def compose_event_persistence_outcome(
    *,
    event_result: EventReplaceResult,
    skipped_event_count: int = 0,
    include_missing_from_source: bool = False,
) -> str:
    """Render the shared detailed persistence summary for event replacements."""

    included_fields = (
        frozenset({"missing_from_source"}) if include_missing_from_source else frozenset()
    )
    return PersistenceOutcomeSummary(
        inserted=event_result.inserted_event_count,
        updated=event_result.updated_event_count,
        unchanged=event_result.unchanged_event_count,
        missing_from_source=event_result.missing_from_source_count,
        skipped=skipped_event_count,
        persisted_event_count=event_result.persisted_event_count,
        included_fields=included_fields,
    ).to_wire()


def require_source_external_id(
    *,
    source_external_id: str | None,
    missing_external_id_message: str,
) -> str:
    """Return a required source external id or raise the connector message."""

    if source_external_id is None:
        raise ValueError(missing_external_id_message)
    return source_external_id


def _resolve_creator_person_id(
    *,
    creator_name: str | None,
    person_repository: PersonRepository,
) -> int | None:
    if creator_name is None:
        return None
    return person_repository.get_or_create(name=creator_name).id


__all__ = [
    "AssetCandidateLike",
    "AssetPersonLike",
    "SourceCandidateLike",
    "compose_event_persistence_outcome",
    "count_missing_events_for_source",
    "persist_asset_candidate",
    "replace_asset_person_links",
    "replace_asset_tag_links",
    "replace_events_for_source",
    "require_source_external_id",
    "resolve_asset_persistence_outcome",
    "upsert_required_source",
]
