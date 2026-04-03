"""Repositories for album-level person-group aggregate derivation and lookup."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from pixelpast.persistence.models import (
    Asset,
    AssetCollection,
    AssetCollectionItem,
    AssetCollectionPersonGroup,
    AssetFolder,
    AssetFolderPersonGroup,
    AssetPerson,
    PersonGroup,
    PersonGroupMember,
    Source,
)


@dataclass(slots=True, frozen=True)
class AlbumAggregateFolderNodeInput:
    """Canonical folder node used for descendant-aware aggregation."""

    folder_id: int
    source_id: int
    parent_id: int | None
    name: str
    path: str


@dataclass(slots=True, frozen=True)
class AlbumAggregateCollectionNodeInput:
    """Canonical collection node used for descendant-aware aggregation."""

    collection_id: int
    source_id: int
    parent_id: int | None
    name: str
    path: str
    collection_type: str


@dataclass(slots=True, frozen=True)
class AlbumAggregateAssetEvidenceInput:
    """Canonical per-asset person evidence used by the album aggregate derive."""

    asset_id: int
    folder_id: int | None
    creator_person_id: int | None
    person_ids: tuple[int, ...]


@dataclass(slots=True, frozen=True)
class AlbumAggregateCollectionMembershipInput:
    """Canonical direct collection membership for one asset."""

    asset_id: int
    collection_id: int


@dataclass(slots=True, frozen=True)
class AlbumAggregatePersonGroupInput:
    """Canonical group membership set for one person group."""

    group_id: int
    name: str
    path: str | None
    person_ids: tuple[int, ...]
    ignored_person_ids: tuple[int, ...]


@dataclass(slots=True, frozen=True)
class AssetFolderPersonGroupSnapshot:
    """Derived folder-to-group relevance row ready for persistence."""

    folder_id: int
    group_id: int
    matched_person_count: int
    group_person_count: int
    matched_asset_count: int
    matched_creator_person_count: int


@dataclass(slots=True, frozen=True)
class AssetCollectionPersonGroupSnapshot:
    """Derived collection-to-group relevance row ready for persistence."""

    collection_id: int
    group_id: int
    matched_person_count: int
    group_person_count: int
    matched_asset_count: int
    matched_creator_person_count: int


@dataclass(slots=True, frozen=True)
class AlbumFolderPersonGroupSnapshot:
    """Readable folder-scoped person-group relevance snapshot."""

    group_id: int
    group_name: str
    group_path: str | None
    matched_person_count: int
    group_person_count: int
    matched_asset_count: int
    matched_creator_person_count: int


@dataclass(slots=True, frozen=True)
class AlbumCollectionPersonGroupSnapshot:
    """Readable collection-scoped person-group relevance snapshot."""

    group_id: int
    group_name: str
    group_path: str | None
    matched_person_count: int
    group_person_count: int
    matched_asset_count: int
    matched_creator_person_count: int


@dataclass(slots=True, frozen=True)
class PersonGroupFolderRelevanceSnapshot:
    """Readable folder relevance row for one selected person group."""

    folder_id: int
    source_id: int
    source_name: str
    source_type: str
    name: str
    path: str
    matched_person_count: int
    group_person_count: int
    matched_asset_count: int
    matched_creator_person_count: int


@dataclass(slots=True, frozen=True)
class PersonGroupCollectionRelevanceSnapshot:
    """Readable collection relevance row for one selected person group."""

    collection_id: int
    source_id: int
    source_name: str
    source_type: str
    name: str
    path: str
    collection_type: str
    matched_person_count: int
    group_person_count: int
    matched_asset_count: int
    matched_creator_person_count: int


class AlbumAggregateRepository:
    """Repository for album aggregate canonical loading, persistence, and reads."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_folder_nodes(self) -> tuple[AlbumAggregateFolderNodeInput, ...]:
        """Return canonical folder nodes in deterministic order."""

        statement = select(
            AssetFolder.id,
            AssetFolder.source_id,
            AssetFolder.parent_id,
            AssetFolder.name,
            AssetFolder.path,
        ).order_by(AssetFolder.source_id, AssetFolder.path, AssetFolder.id)
        return tuple(
            AlbumAggregateFolderNodeInput(
                folder_id=folder_id,
                source_id=source_id,
                parent_id=parent_id,
                name=name,
                path=path,
            )
            for folder_id, source_id, parent_id, name, path in self._session.execute(
                statement
            )
        )

    def list_collection_nodes(self) -> tuple[AlbumAggregateCollectionNodeInput, ...]:
        """Return canonical collection nodes in deterministic order."""

        statement = select(
            AssetCollection.id,
            AssetCollection.source_id,
            AssetCollection.parent_id,
            AssetCollection.name,
            AssetCollection.path,
            AssetCollection.collection_type,
        ).order_by(AssetCollection.source_id, AssetCollection.path, AssetCollection.id)
        return tuple(
            AlbumAggregateCollectionNodeInput(
                collection_id=collection_id,
                source_id=source_id,
                parent_id=parent_id,
                name=name,
                path=path,
                collection_type=collection_type,
            )
            for (
                collection_id,
                source_id,
                parent_id,
                name,
                path,
                collection_type,
            ) in self._session.execute(statement)
        )

    def list_asset_evidence(self) -> tuple[AlbumAggregateAssetEvidenceInput, ...]:
        """Return canonical per-asset person evidence in deterministic order."""

        asset_rows = list(
            self._session.execute(
                select(
                    Asset.id,
                    Asset.folder_id,
                    Asset.creator_person_id,
                ).order_by(Asset.id)
            )
        )
        if not asset_rows:
            return ()

        asset_ids = [asset_id for asset_id, _, _ in asset_rows]
        person_rows = self._session.execute(
            select(AssetPerson.asset_id, AssetPerson.person_id)
            .where(AssetPerson.asset_id.in_(asset_ids))
            .order_by(AssetPerson.asset_id, AssetPerson.person_id)
        )
        person_ids_by_asset_id: dict[int, list[int]] = {asset_id: [] for asset_id in asset_ids}
        for asset_id, person_id in person_rows:
            person_ids_by_asset_id.setdefault(asset_id, []).append(person_id)

        return tuple(
            AlbumAggregateAssetEvidenceInput(
                asset_id=asset_id,
                folder_id=folder_id,
                creator_person_id=creator_person_id,
                person_ids=tuple(sorted(set(person_ids_by_asset_id.get(asset_id, [])))),
            )
            for asset_id, folder_id, creator_person_id in asset_rows
        )

    def list_collection_memberships(
        self,
    ) -> tuple[AlbumAggregateCollectionMembershipInput, ...]:
        """Return direct asset-to-collection memberships in deterministic order."""

        statement = select(
            AssetCollectionItem.asset_id,
            AssetCollectionItem.collection_id,
        ).order_by(AssetCollectionItem.asset_id, AssetCollectionItem.collection_id)
        return tuple(
            AlbumAggregateCollectionMembershipInput(
                asset_id=asset_id,
                collection_id=collection_id,
            )
            for asset_id, collection_id in self._session.execute(statement)
        )

    def list_person_groups(self) -> tuple[AlbumAggregatePersonGroupInput, ...]:
        """Return person groups and their canonical member sets."""

        group_rows = list(
            self._session.execute(
                select(
                    PersonGroup.id,
                    PersonGroup.name,
                    PersonGroup.path,
                    PersonGroup.metadata_json,
                ).order_by(
                    func.lower(PersonGroup.name),
                    PersonGroup.id,
                )
            )
        )
        if not group_rows:
            return ()

        group_ids = [group_id for group_id, _, _, _ in group_rows]
        member_rows = self._session.execute(
            select(PersonGroupMember.group_id, PersonGroupMember.person_id)
            .where(PersonGroupMember.group_id.in_(group_ids))
            .order_by(PersonGroupMember.group_id, PersonGroupMember.person_id)
        )
        person_ids_by_group_id: dict[int, list[int]] = {group_id: [] for group_id in group_ids}
        for group_id, person_id in member_rows:
            person_ids_by_group_id.setdefault(group_id, []).append(person_id)

        return tuple(
            AlbumAggregatePersonGroupInput(
                group_id=group_id,
                name=name,
                path=path,
                person_ids=tuple(sorted(set(person_ids_by_group_id.get(group_id, [])))),
                ignored_person_ids=tuple(
                    _normalize_album_aggregate_ignored_person_ids(metadata_json)
                ),
            )
            for group_id, name, path, metadata_json in group_rows
        )

    def replace_all(
        self,
        *,
        folder_rows: tuple[AssetFolderPersonGroupSnapshot, ...],
        collection_rows: tuple[AssetCollectionPersonGroupSnapshot, ...],
    ) -> None:
        """Replace the full album aggregate materialization deterministically."""

        self._session.execute(delete(AssetFolderPersonGroup))
        self._session.execute(delete(AssetCollectionPersonGroup))

        if folder_rows:
            self._session.add_all(
                [
                    AssetFolderPersonGroup(
                        folder_id=row.folder_id,
                        group_id=row.group_id,
                        matched_person_count=row.matched_person_count,
                        group_person_count=row.group_person_count,
                        matched_asset_count=row.matched_asset_count,
                        matched_creator_person_count=row.matched_creator_person_count,
                    )
                    for row in folder_rows
                ]
            )
        if collection_rows:
            self._session.add_all(
                [
                    AssetCollectionPersonGroup(
                        collection_id=row.collection_id,
                        group_id=row.group_id,
                        matched_person_count=row.matched_person_count,
                        group_person_count=row.group_person_count,
                        matched_asset_count=row.matched_asset_count,
                        matched_creator_person_count=row.matched_creator_person_count,
                    )
                    for row in collection_rows
                ]
            )
        self._session.flush()

    def list_person_groups_for_folder(
        self,
        *,
        folder_id: int,
    ) -> tuple[AlbumFolderPersonGroupSnapshot, ...]:
        """Return relevant person groups for one folder subtree."""

        statement = (
            select(
                PersonGroup.id,
                PersonGroup.name,
                PersonGroup.path,
                AssetFolderPersonGroup.matched_person_count,
                AssetFolderPersonGroup.group_person_count,
                AssetFolderPersonGroup.matched_asset_count,
                AssetFolderPersonGroup.matched_creator_person_count,
            )
            .join(
                AssetFolderPersonGroup,
                AssetFolderPersonGroup.group_id == PersonGroup.id,
            )
            .where(AssetFolderPersonGroup.folder_id == folder_id)
            .order_by(
                AssetFolderPersonGroup.matched_person_count.desc(),
                AssetFolderPersonGroup.matched_asset_count.desc(),
                func.lower(PersonGroup.name),
                PersonGroup.id,
            )
        )
        return tuple(
            AlbumFolderPersonGroupSnapshot(
                group_id=group_id,
                group_name=group_name,
                group_path=group_path,
                matched_person_count=matched_person_count,
                group_person_count=group_person_count,
                matched_asset_count=matched_asset_count,
                matched_creator_person_count=matched_creator_person_count,
            )
            for (
                group_id,
                group_name,
                group_path,
                matched_person_count,
                group_person_count,
                matched_asset_count,
                matched_creator_person_count,
            ) in self._session.execute(statement)
        )

    def list_person_groups_for_collection(
        self,
        *,
        collection_id: int,
    ) -> tuple[AlbumCollectionPersonGroupSnapshot, ...]:
        """Return relevant person groups for one collection subtree."""

        statement = (
            select(
                PersonGroup.id,
                PersonGroup.name,
                PersonGroup.path,
                AssetCollectionPersonGroup.matched_person_count,
                AssetCollectionPersonGroup.group_person_count,
                AssetCollectionPersonGroup.matched_asset_count,
                AssetCollectionPersonGroup.matched_creator_person_count,
            )
            .join(
                AssetCollectionPersonGroup,
                AssetCollectionPersonGroup.group_id == PersonGroup.id,
            )
            .where(AssetCollectionPersonGroup.collection_id == collection_id)
            .order_by(
                AssetCollectionPersonGroup.matched_person_count.desc(),
                AssetCollectionPersonGroup.matched_asset_count.desc(),
                func.lower(PersonGroup.name),
                PersonGroup.id,
            )
        )
        return tuple(
            AlbumCollectionPersonGroupSnapshot(
                group_id=group_id,
                group_name=group_name,
                group_path=group_path,
                matched_person_count=matched_person_count,
                group_person_count=group_person_count,
                matched_asset_count=matched_asset_count,
                matched_creator_person_count=matched_creator_person_count,
            )
            for (
                group_id,
                group_name,
                group_path,
                matched_person_count,
                group_person_count,
                matched_asset_count,
                matched_creator_person_count,
            ) in self._session.execute(statement)
        )

    def list_folders_for_person_group(
        self,
        *,
        group_id: int,
    ) -> tuple[PersonGroupFolderRelevanceSnapshot, ...]:
        """Return relevant folders for one person group."""

        statement = (
            select(
                AssetFolder.id,
                AssetFolder.source_id,
                Source.name,
                Source.type,
                AssetFolder.name,
                AssetFolder.path,
                AssetFolderPersonGroup.matched_person_count,
                AssetFolderPersonGroup.group_person_count,
                AssetFolderPersonGroup.matched_asset_count,
                AssetFolderPersonGroup.matched_creator_person_count,
            )
            .join(AssetFolderPersonGroup, AssetFolderPersonGroup.folder_id == AssetFolder.id)
            .join(Source, Source.id == AssetFolder.source_id)
            .where(AssetFolderPersonGroup.group_id == group_id)
            .order_by(
                AssetFolderPersonGroup.matched_person_count.desc(),
                AssetFolderPersonGroup.matched_asset_count.desc(),
                func.lower(AssetFolder.path),
                AssetFolder.id,
            )
        )
        return tuple(
            PersonGroupFolderRelevanceSnapshot(
                folder_id=folder_id,
                source_id=source_id,
                source_name=source_name,
                source_type=source_type,
                name=name,
                path=path,
                matched_person_count=matched_person_count,
                group_person_count=group_person_count,
                matched_asset_count=matched_asset_count,
                matched_creator_person_count=matched_creator_person_count,
            )
            for (
                folder_id,
                source_id,
                source_name,
                source_type,
                name,
                path,
                matched_person_count,
                group_person_count,
                matched_asset_count,
                matched_creator_person_count,
            ) in self._session.execute(statement)
        )

    def list_collections_for_person_group(
        self,
        *,
        group_id: int,
    ) -> tuple[PersonGroupCollectionRelevanceSnapshot, ...]:
        """Return relevant collections for one person group."""

        statement = (
            select(
                AssetCollection.id,
                AssetCollection.source_id,
                Source.name,
                Source.type,
                AssetCollection.name,
                AssetCollection.path,
                AssetCollection.collection_type,
                AssetCollectionPersonGroup.matched_person_count,
                AssetCollectionPersonGroup.group_person_count,
                AssetCollectionPersonGroup.matched_asset_count,
                AssetCollectionPersonGroup.matched_creator_person_count,
            )
            .join(
                AssetCollectionPersonGroup,
                AssetCollectionPersonGroup.collection_id == AssetCollection.id,
            )
            .join(Source, Source.id == AssetCollection.source_id)
            .where(AssetCollectionPersonGroup.group_id == group_id)
            .order_by(
                AssetCollectionPersonGroup.matched_person_count.desc(),
                AssetCollectionPersonGroup.matched_asset_count.desc(),
                func.lower(AssetCollection.path),
                AssetCollection.id,
            )
        )
        return tuple(
            PersonGroupCollectionRelevanceSnapshot(
                collection_id=collection_id,
                source_id=source_id,
                source_name=source_name,
                source_type=source_type,
                name=name,
                path=path,
                collection_type=collection_type,
                matched_person_count=matched_person_count,
                group_person_count=group_person_count,
                matched_asset_count=matched_asset_count,
                matched_creator_person_count=matched_creator_person_count,
            )
            for (
                collection_id,
                source_id,
                source_name,
                source_type,
                name,
                path,
                collection_type,
                matched_person_count,
                group_person_count,
                matched_asset_count,
                matched_creator_person_count,
            ) in self._session.execute(statement)
        )


def _normalize_album_aggregate_ignored_person_ids(
    metadata_json: Any,
) -> tuple[int, ...]:
    if not isinstance(metadata_json, dict):
        return ()
    album_aggregate = metadata_json.get("album_aggregate")
    if not isinstance(album_aggregate, dict):
        return ()
    raw_ignored_person_ids = album_aggregate.get("ignored_person_ids")
    if not isinstance(raw_ignored_person_ids, list):
        return ()
    normalized_ids: list[int] = []
    seen_ids: set[int] = set()
    for value in raw_ignored_person_ids:
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            continue
        if value in seen_ids:
            continue
        normalized_ids.append(value)
        seen_ids.add(value)
    return tuple(sorted(normalized_ids))
