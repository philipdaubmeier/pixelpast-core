"""Canonical repositories for source state and operational job runs."""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from pixelpast.domain.entities import (
    AlbumNavigationFillInResult,
    AssetCollectionItemRecord,
    AssetCollectionRecord,
    AssetFolderRecord,
)
from pixelpast.persistence.asset_short_ids import (
    build_asset_short_id_candidate,
    generate_random_asset_short_id,
)
from pixelpast.persistence.models import (
    Asset,
    AssetCollection,
    AssetCollectionItem,
    AssetFolder,
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


@dataclass(slots=True, frozen=True)
class AssetThumbnailCandidate:
    """One canonical asset row enriched with source context for media work."""

    asset_id: int
    short_id: str
    external_id: str
    media_type: str
    metadata_json: dict[str, Any] | None
    source_type: str


@dataclass(slots=True, frozen=True)
class AssetOriginalCandidate:
    """One canonical asset row enriched for original-media file resolution."""

    asset_id: int
    short_id: str
    external_id: str
    media_type: str
    metadata_json: dict[str, Any] | None
    source_type: str
    source_config: dict[str, Any]


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
        folder_id: int | None = None,
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
                folder_id=folder_id,
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
                asset.folder_id != folder_id,
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
            asset.folder_id = folder_id
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
        folder_id: int | None = None,
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
                folder_id=folder_id,
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


class AssetMediaRepository:
    """Read repository for canonical asset media derivation workloads."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_thumbnail_candidates(self) -> tuple[AssetThumbnailCandidate, ...]:
        """Return deterministic photo assets together with their source type."""

        statement = (
            select(
                Asset.id,
                Asset.short_id,
                Asset.external_id,
                Asset.media_type,
                Asset.metadata_json,
                Source.type,
            )
            .join(Source, Source.id == Asset.source_id)
            .where(Asset.media_type == "photo")
            .order_by(Asset.short_id, Asset.id)
        )
        return tuple(
            AssetThumbnailCandidate(
                asset_id=asset_id,
                short_id=short_id,
                external_id=external_id,
                media_type=media_type,
                metadata_json=metadata_json,
                source_type=source_type,
            )
            for (
                asset_id,
                short_id,
                external_id,
                media_type,
                metadata_json,
                source_type,
            ) in self._session.execute(statement)
        )

    def get_thumbnail_candidate_by_short_id(
        self,
        *,
        short_id: str,
    ) -> AssetThumbnailCandidate | None:
        """Return one thumbnail candidate resolved by the public asset short id."""

        statement = (
            select(
                Asset.id,
                Asset.short_id,
                Asset.external_id,
                Asset.media_type,
                Asset.metadata_json,
                Source.type,
            )
            .join(Source, Source.id == Asset.source_id)
            .where(Asset.short_id == short_id)
            .order_by(Asset.id)
        )
        row = self._session.execute(statement).first()
        if row is None:
            return None

        return AssetThumbnailCandidate(
            asset_id=row[0],
            short_id=row[1],
            external_id=row[2],
            media_type=row[3],
            metadata_json=row[4],
            source_type=row[5],
        )

    def get_original_candidate_by_short_id(
        self,
        *,
        short_id: str,
    ) -> AssetOriginalCandidate | None:
        """Return one original-media candidate resolved by public short id."""

        statement = (
            select(
                Asset.id,
                Asset.short_id,
                Asset.external_id,
                Asset.media_type,
                Asset.metadata_json,
                Source.type,
                Source.config,
            )
            .join(Source, Source.id == Asset.source_id)
            .where(Asset.short_id == short_id)
            .order_by(Asset.id)
        )
        row = self._session.execute(statement).first()
        if row is None:
            return None

        source_config = row[6]
        return AssetOriginalCandidate(
            asset_id=row[0],
            short_id=row[1],
            external_id=row[2],
            media_type=row[3],
            metadata_json=row[4],
            source_type=row[5],
            source_config=source_config if isinstance(source_config, dict) else {},
        )


class AssetFolderRepository:
    """Repository for canonical physical album-folder storage."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_source_and_path(
        self,
        *,
        source_id: int,
        path: str,
    ) -> AssetFolder | None:
        statement = select(AssetFolder).where(
            AssetFolder.source_id == source_id,
            AssetFolder.path == path,
        )
        return self._session.execute(statement).scalar_one_or_none()

    def list_by_source_id(self, *, source_id: int) -> tuple[AssetFolderRecord, ...]:
        statement = (
            select(AssetFolder)
            .where(AssetFolder.source_id == source_id)
            .order_by(AssetFolder.path, AssetFolder.id)
        )
        return tuple(
            AssetFolderRecord(
                id=folder.id,
                source_id=folder.source_id,
                parent_id=folder.parent_id,
                name=folder.name,
                path=folder.path,
            )
            for folder in self._session.execute(statement).scalars()
        )

    def get_or_create_tree(
        self,
        *,
        source_id: int,
        path: str,
    ) -> tuple[AssetFolder, int]:
        normalized_path = _normalize_navigation_path(path)
        if normalized_path is None:
            raise ValueError("Asset folder path must not be empty.")

        created_count = 0
        parent: AssetFolder | None = None
        prefix_segments: list[str] = []

        for segment in normalized_path.split("/"):
            prefix_segments.append(segment)
            segment_path = "/".join(prefix_segments)
            folder = self.get_by_source_and_path(
                source_id=source_id,
                path=segment_path,
            )
            if folder is None:
                folder = AssetFolder(
                    source_id=source_id,
                    parent_id=parent.id if parent is not None else None,
                    name=segment,
                    path=segment_path,
                )
                self._session.add(folder)
                self._session.flush()
                created_count += 1
            elif folder.parent_id != (parent.id if parent is not None else None):
                folder.parent_id = parent.id if parent is not None else None
                folder.name = segment
                self._session.flush()
            parent = folder

        if parent is None:
            raise ValueError("Asset folder path must not be empty.")
        return parent, created_count


class AssetCollectionRepository:
    """Repository for canonical semantic album-collection storage."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_source_and_external_id(
        self,
        *,
        source_id: int,
        external_id: str,
    ) -> AssetCollection | None:
        statement = select(AssetCollection).where(
            AssetCollection.source_id == source_id,
            AssetCollection.external_id == external_id,
        )
        return self._session.execute(statement).scalar_one_or_none()

    def list_by_source_id(
        self,
        *,
        source_id: int,
    ) -> tuple[AssetCollectionRecord, ...]:
        statement = (
            select(AssetCollection)
            .where(AssetCollection.source_id == source_id)
            .order_by(AssetCollection.path, AssetCollection.id)
        )
        return tuple(
            AssetCollectionRecord(
                id=collection.id,
                source_id=collection.source_id,
                parent_id=collection.parent_id,
                name=collection.name,
                path=collection.path,
                external_id=collection.external_id,
                collection_type=collection.collection_type,
                metadata_json=(
                    dict(collection.metadata_json)
                    if collection.metadata_json is not None
                    else None
                ),
            )
            for collection in self._session.execute(statement).scalars()
        )

    def list_items_by_source_id(
        self,
        *,
        source_id: int,
    ) -> tuple[AssetCollectionItemRecord, ...]:
        statement = (
            select(AssetCollectionItem)
            .join(
                AssetCollection,
                AssetCollection.id == AssetCollectionItem.collection_id,
            )
            .where(AssetCollection.source_id == source_id)
            .order_by(
                AssetCollectionItem.collection_id,
                AssetCollectionItem.asset_id,
            )
        )
        return tuple(
            AssetCollectionItemRecord(
                collection_id=item.collection_id,
                asset_id=item.asset_id,
            )
            for item in self._session.execute(statement).scalars()
        )

    def upsert(
        self,
        *,
        source_id: int,
        external_id: str,
        name: str,
        path: str,
        collection_type: str,
        metadata_json: dict[str, Any] | None = None,
    ) -> tuple[AssetCollection, str]:
        collection = self.get_by_source_and_external_id(
            source_id=source_id,
            external_id=external_id,
        )
        normalized_path = _normalize_navigation_path(path)
        if normalized_path is None:
            raise ValueError("Asset collection path must not be empty.")

        next_metadata = dict(metadata_json) if metadata_json is not None else None
        if collection is None:
            collection = AssetCollection(
                source_id=source_id,
                parent_id=None,
                name=name,
                path=normalized_path,
                external_id=external_id,
                collection_type=collection_type,
                metadata_json=next_metadata,
            )
            self._session.add(collection)
            self._session.flush()
            return collection, "inserted"

        changed = any(
            [
                collection.name != name,
                collection.path != normalized_path,
                collection.collection_type != collection_type,
                collection.metadata_json != next_metadata,
            ]
        )
        if changed:
            collection.name = name
            collection.path = normalized_path
            collection.collection_type = collection_type
            collection.metadata_json = next_metadata
            self._session.flush()
            return collection, "updated"
        return collection, "unchanged"

    def reconcile_parent_links(self, *, source_id: int) -> None:
        collections = list(
            self._session.execute(
                select(AssetCollection)
                .where(AssetCollection.source_id == source_id)
                .order_by(AssetCollection.path, AssetCollection.id)
            ).scalars()
        )
        by_path = {collection.path: collection for collection in collections}
        for collection in collections:
            parent_path = _parent_navigation_path(collection.path)
            parent_id = by_path[parent_path].id if parent_path in by_path else None
            if collection.parent_id != parent_id:
                collection.parent_id = parent_id
        self._session.flush()

    def replace_items_for_source(
        self,
        *,
        source_id: int,
        memberships: Iterable[tuple[int, int]],
    ) -> int:
        self._session.execute(
            delete(AssetCollectionItem).where(
                AssetCollectionItem.collection_id.in_(
                    select(AssetCollection.id).where(
                        AssetCollection.source_id == source_id
                    )
                )
            )
        )
        unique_memberships = sorted(set(memberships))
        self._session.add_all(
            [
                AssetCollectionItem(collection_id=collection_id, asset_id=asset_id)
                for collection_id, asset_id in unique_memberships
            ]
        )
        self._session.flush()
        return len(unique_memberships)


class AlbumNavigationRepository:
    """Repository for album-navigation fill-in based on existing asset metadata."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._folders = AssetFolderRepository(session)
        self._collections = AssetCollectionRepository(session)

    def fill_from_existing_assets(
        self,
        *,
        source_id: int | None = None,
    ) -> AlbumNavigationFillInResult:
        statement = (
            select(Asset, Source)
            .join(Source, Source.id == Asset.source_id)
            .order_by(Source.id, Asset.id)
        )
        if source_id is not None:
            statement = statement.where(Source.id == source_id)

        rows = self._session.execute(statement).all()
        created_folder_count = 0
        created_collection_count = 0
        assigned_asset_folder_count = 0
        unresolved_asset_count = 0
        collection_memberships: dict[int, set[tuple[int, int]]] = {}

        for asset, source in rows:
            folder_path = _extract_folder_path_from_asset(
                asset=asset,
                source=source,
            )
            if folder_path is None:
                if asset.folder_id is None:
                    unresolved_asset_count += 1
            else:
                folder, created_count = self._folders.get_or_create_tree(
                    source_id=source.id,
                    path=folder_path,
                )
                created_folder_count += created_count
                if asset.folder_id != folder.id:
                    asset.folder_id = folder.id
                    assigned_asset_folder_count += 1

            for spec in _extract_collection_specs_from_asset(asset=asset):
                collection, status = self._collections.upsert(
                    source_id=source.id,
                    external_id=spec.external_id,
                    name=spec.name,
                    path=spec.path,
                    collection_type=spec.collection_type,
                    metadata_json=spec.metadata_json,
                )
                if status == "inserted":
                    created_collection_count += 1
                collection_memberships.setdefault(source.id, set()).add(
                    (collection.id, asset.id)
                )

        linked_collection_item_count = 0
        for resolved_source_id, memberships in sorted(collection_memberships.items()):
            self._collections.reconcile_parent_links(source_id=resolved_source_id)
            linked_collection_item_count += self._collections.replace_items_for_source(
                source_id=resolved_source_id,
                memberships=memberships,
            )

        self._session.flush()
        return AlbumNavigationFillInResult(
            created_folder_count=created_folder_count,
            created_collection_count=created_collection_count,
            assigned_asset_folder_count=assigned_asset_folder_count,
            linked_collection_item_count=linked_collection_item_count,
            unresolved_asset_count=unresolved_asset_count,
        )

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
                _build_event_model(
                    source_id=source_id,
                    event=next_by_identity[identity],
                )
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


@dataclass(slots=True, frozen=True)
class _AssetCollectionFillInSpec:
    external_id: str
    name: str
    path: str
    collection_type: str
    metadata_json: dict[str, Any] | None


def _extract_folder_path_from_asset(*, asset: Asset, source: Source) -> str | None:
    metadata_json = asset.metadata_json if isinstance(asset.metadata_json, dict) else {}

    if source.type == "photos":
        source_path = metadata_json.get("source_path")
        root_path = source.config.get("root_path") if isinstance(source.config, dict) else None
        return _build_photo_folder_path(
            source_path=source_path if isinstance(source_path, str) else None,
            root_path=root_path if isinstance(root_path, str) else None,
        )

    file_path = metadata_json.get("file_path")
    if isinstance(file_path, str):
        return _normalize_filesystem_folder_path(file_path)
    return None


def _build_photo_folder_path(
    *,
    source_path: str | None,
    root_path: str | None,
) -> str | None:
    normalized_source_path = _normalize_path_string(source_path)
    if normalized_source_path is None:
        return None

    source_file_path = PurePosixPath(normalized_source_path)
    if source_file_path.parent == source_file_path:
        return None

    normalized_root_path = _normalize_path_string(root_path)
    if normalized_root_path is None:
        return _normalize_navigation_path(source_file_path.parent.as_posix())

    root = PurePosixPath(normalized_root_path)
    try:
        relative_parent = source_file_path.parent.relative_to(root)
    except ValueError:
        return _normalize_navigation_path(source_file_path.parent.as_posix())

    segments = [segment for segment in (root.name, *relative_parent.parts) if segment not in {"", "."}]
    return _normalize_navigation_path("/".join(segments))


def _normalize_filesystem_folder_path(file_path: str) -> str | None:
    normalized_file_path = _normalize_path_string(file_path)
    if normalized_file_path is None:
        return None
    parent = PurePosixPath(normalized_file_path).parent
    if parent.as_posix() in {"", "."}:
        return None
    return _normalize_navigation_path(parent.as_posix())


def _extract_collection_specs_from_asset(
    *,
    asset: Asset,
) -> tuple[_AssetCollectionFillInSpec, ...]:
    metadata_json = asset.metadata_json if isinstance(asset.metadata_json, dict) else {}
    raw_collections = metadata_json.get("collections")
    if not isinstance(raw_collections, list):
        return ()

    specs: list[_AssetCollectionFillInSpec] = []
    seen_external_ids: set[str] = set()
    for raw_collection in raw_collections:
        if not isinstance(raw_collection, dict):
            continue

        external_id_value = raw_collection.get("id")
        name_value = raw_collection.get("name")
        path_value = raw_collection.get("path")
        if name_value is None or path_value is None or external_id_value is None:
            continue

        name = str(name_value).strip()
        path = _normalize_navigation_path(str(path_value))
        external_id = str(external_id_value).strip()
        if name == "" or path is None or external_id == "" or external_id in seen_external_ids:
            continue

        seen_external_ids.add(external_id)
        specs.append(
            _AssetCollectionFillInSpec(
                external_id=external_id,
                name=name,
                path=path,
                collection_type="lightroom_collection",
                metadata_json={"fill_in_source": "asset.metadata.collections"},
            )
        )

    return tuple(sorted(specs, key=lambda spec: (spec.path.casefold(), spec.external_id)))


def _normalize_path_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().replace("\\", "/")
    if normalized == "":
        return None
    return normalized


def _normalize_navigation_path(value: str | None) -> str | None:
    normalized = _normalize_path_string(value)
    if normalized is None:
        return None
    segments = [segment.strip() for segment in normalized.split("/") if segment.strip() != ""]
    if not segments:
        return None
    return "/".join(segments)


def _parent_navigation_path(path: str) -> str | None:
    if "/" not in path:
        return None
    parent_path = path.rsplit("/", 1)[0]
    return parent_path or None


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
