"""Read repositories for album-navigation trees and asset listings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from pixelpast.persistence.models import (
    Asset,
    AssetCollection,
    AssetCollectionItem,
    AssetFolder,
    AssetPerson,
    AssetTag,
    Person,
    Source,
    Tag,
)


@dataclass(frozen=True, slots=True)
class AlbumQueryFilters:
    """Normalized supported persistent filters for album reads."""

    person_ids: tuple[int, ...] = ()
    tag_paths: tuple[str, ...] = ()
    filename_query: str | None = None


@dataclass(frozen=True, slots=True)
class AlbumFolderTreeNodeSnapshot:
    """Serializable folder-tree node with filtered aggregate counts."""

    id: int
    source_id: int
    source_name: str
    source_type: str
    parent_id: int | None
    name: str
    path: str
    child_count: int
    asset_count: int


@dataclass(frozen=True, slots=True)
class AlbumCollectionTreeNodeSnapshot:
    """Serializable collection-tree node with filtered aggregate counts."""

    id: int
    source_id: int
    source_name: str
    source_type: str
    parent_id: int | None
    name: str
    path: str
    collection_type: str
    child_count: int
    asset_count: int


@dataclass(frozen=True, slots=True)
class AlbumSelectionSnapshot:
    """Serializable selected album node summary for one asset listing."""

    node_kind: str
    id: int
    source_id: int
    source_name: str
    source_type: str
    parent_id: int | None
    name: str
    path: str
    asset_count: int
    collection_type: str | None = None


@dataclass(frozen=True, slots=True)
class AlbumAssetListItemSnapshot:
    """Serializable album asset row suitable for thumbnail-grid browsing."""

    id: int
    short_id: str
    timestamp_iso: str
    media_type: str
    title: str


@dataclass(frozen=True, slots=True)
class AlbumAssetListingSnapshot:
    """Serializable album asset-list response body."""

    selection: AlbumSelectionSnapshot
    items: tuple[AlbumAssetListItemSnapshot, ...]


@dataclass(frozen=True, slots=True)
class _FolderNodeRow:
    id: int
    source_id: int
    source_name: str
    source_type: str
    parent_id: int | None
    name: str
    path: str


@dataclass(frozen=True, slots=True)
class _CollectionNodeRow:
    id: int
    source_id: int
    source_name: str
    source_type: str
    parent_id: int | None
    name: str
    path: str
    collection_type: str


@dataclass(frozen=True, slots=True)
class _AssetRow:
    id: int
    short_id: str
    source_id: int
    timestamp_iso: str
    media_type: str
    external_id: str
    summary: str | None
    metadata_json: dict[str, Any] | None
    folder_id: int | None


class AlbumNavigationReadRepository:
    """Load explicit album trees and node-scoped asset listings."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_folder_tree(
        self,
        *,
        filters: AlbumQueryFilters,
    ) -> tuple[AlbumFolderTreeNodeSnapshot, ...]:
        """Return the physical folder tree with filtered descendant asset counts."""

        nodes = self._list_folder_nodes()
        counts = self._count_assets_by_folder_subtree(filters=filters, nodes=nodes)
        child_counts = _count_children_by_parent_id(node.parent_id for node in nodes)
        ordered_nodes = sorted(
            nodes,
            key=lambda node: (
                node.source_name.casefold(),
                node.source_id,
                node.path.casefold(),
                node.id,
            ),
        )
        return tuple(
            AlbumFolderTreeNodeSnapshot(
                id=node.id,
                source_id=node.source_id,
                source_name=node.source_name,
                source_type=node.source_type,
                parent_id=node.parent_id,
                name=node.name,
                path=node.path,
                child_count=child_counts.get(node.id, 0),
                asset_count=counts.get(node.id, 0),
            )
            for node in ordered_nodes
        )

    def list_collection_tree(
        self,
        *,
        filters: AlbumQueryFilters,
    ) -> tuple[AlbumCollectionTreeNodeSnapshot, ...]:
        """Return the semantic collection tree with filtered asset counts."""

        nodes = self._list_collection_nodes()
        counts = self._count_assets_by_collection_subtree(filters=filters, nodes=nodes)
        child_counts = _count_children_by_parent_id(node.parent_id for node in nodes)
        ordered_nodes = sorted(
            nodes,
            key=lambda node: (
                node.source_name.casefold(),
                node.source_id,
                node.path.casefold(),
                node.id,
            ),
        )
        return tuple(
            AlbumCollectionTreeNodeSnapshot(
                id=node.id,
                source_id=node.source_id,
                source_name=node.source_name,
                source_type=node.source_type,
                parent_id=node.parent_id,
                name=node.name,
                path=node.path,
                collection_type=node.collection_type,
                child_count=child_counts.get(node.id, 0),
                asset_count=counts.get(node.id, 0),
            )
            for node in ordered_nodes
        )

    def get_folder_asset_listing(
        self,
        *,
        folder_id: int,
        filters: AlbumQueryFilters,
    ) -> AlbumAssetListingSnapshot | None:
        """Return the filtered asset listing for one folder subtree selection."""

        nodes = self._list_folder_nodes()
        selected_node = next((node for node in nodes if node.id == folder_id), None)
        if selected_node is None:
            return None

        descendant_ids = {
            node.id
            for node in nodes
            if node.source_id == selected_node.source_id
            and _is_navigation_descendant(
                candidate_path=node.path,
                selected_path=selected_node.path,
            )
        }
        filtered_assets = self._list_filtered_assets(filters=filters)
        selected_assets = [
            asset for asset in filtered_assets if asset.folder_id in descendant_ids
        ]
        return AlbumAssetListingSnapshot(
            selection=AlbumSelectionSnapshot(
                node_kind="folder",
                id=selected_node.id,
                source_id=selected_node.source_id,
                source_name=selected_node.source_name,
                source_type=selected_node.source_type,
                parent_id=selected_node.parent_id,
                name=selected_node.name,
                path=selected_node.path,
                asset_count=len(selected_assets),
            ),
            items=tuple(self._to_listing_item(asset) for asset in selected_assets),
        )

    def get_collection_asset_listing(
        self,
        *,
        collection_id: int,
        filters: AlbumQueryFilters,
    ) -> AlbumAssetListingSnapshot | None:
        """Return the filtered asset listing for one collection subtree selection."""

        nodes = self._list_collection_nodes()
        selected_node = next((node for node in nodes if node.id == collection_id), None)
        if selected_node is None:
            return None

        descendant_collection_ids = {
            node.id
            for node in nodes
            if node.source_id == selected_node.source_id
            and _is_navigation_descendant(
                candidate_path=node.path,
                selected_path=selected_node.path,
            )
        }
        filtered_assets = self._list_filtered_assets(filters=filters)
        memberships_by_asset_id = self._list_collection_memberships_by_asset(
            asset_ids=[asset.id for asset in filtered_assets]
        )
        selected_assets = [
            asset
            for asset in filtered_assets
            if descendant_collection_ids.intersection(
                memberships_by_asset_id.get(asset.id, set())
            )
        ]
        return AlbumAssetListingSnapshot(
            selection=AlbumSelectionSnapshot(
                node_kind="collection",
                id=selected_node.id,
                source_id=selected_node.source_id,
                source_name=selected_node.source_name,
                source_type=selected_node.source_type,
                parent_id=selected_node.parent_id,
                name=selected_node.name,
                path=selected_node.path,
                asset_count=len(selected_assets),
                collection_type=selected_node.collection_type,
            ),
            items=tuple(self._to_listing_item(asset) for asset in selected_assets),
        )

    def _list_folder_nodes(self) -> list[_FolderNodeRow]:
        rows = self._session.execute(
            select(
                AssetFolder.id,
                AssetFolder.source_id,
                Source.name,
                Source.type,
                AssetFolder.parent_id,
                AssetFolder.name,
                AssetFolder.path,
            ).join(Source, Source.id == AssetFolder.source_id)
        )
        return [
            _FolderNodeRow(
                id=folder_id,
                source_id=source_id,
                source_name=source_name,
                source_type=source_type,
                parent_id=parent_id,
                name=name,
                path=path,
            )
            for folder_id, source_id, source_name, source_type, parent_id, name, path in rows
        ]

    def _list_collection_nodes(self) -> list[_CollectionNodeRow]:
        rows = self._session.execute(
            select(
                AssetCollection.id,
                AssetCollection.source_id,
                Source.name,
                Source.type,
                AssetCollection.parent_id,
                AssetCollection.name,
                AssetCollection.path,
                AssetCollection.collection_type,
            ).join(Source, Source.id == AssetCollection.source_id)
        )
        return [
            _CollectionNodeRow(
                id=collection_id,
                source_id=source_id,
                source_name=source_name,
                source_type=source_type,
                parent_id=parent_id,
                name=name,
                path=path,
                collection_type=collection_type,
            )
            for (
                collection_id,
                source_id,
                source_name,
                source_type,
                parent_id,
                name,
                path,
                collection_type,
            ) in rows
        ]

    def _list_filtered_assets(self, *, filters: AlbumQueryFilters) -> list[_AssetRow]:
        assets = self._list_all_assets()
        if not assets:
            return []

        person_links_by_asset: dict[int, set[int]] = {}
        if filters.person_ids:
            person_links_by_asset = self._list_person_links_by_asset(
                asset_ids=[asset.id for asset in assets]
            )

        tag_links_by_asset: dict[int, list[str]] = {}
        if filters.tag_paths:
            tag_links_by_asset = self._list_tag_links_by_asset(
                asset_ids=[asset.id for asset in assets]
            )

        filtered_assets: list[_AssetRow] = []
        normalized_filename_query = (
            filters.filename_query.casefold().strip()
            if filters.filename_query is not None
            else None
        )
        for asset in assets:
            if filters.person_ids and not person_links_by_asset.get(asset.id, set()).intersection(
                filters.person_ids
            ):
                continue
            if filters.tag_paths and not any(
                _tag_path_matches_selection(
                    asset_tag_path=asset_tag_path,
                    selected_tag_path=selected_tag_path,
                )
                for asset_tag_path in tag_links_by_asset.get(asset.id, [])
                for selected_tag_path in filters.tag_paths
            ):
                continue
            if normalized_filename_query is not None and not any(
                normalized_filename_query in filename.casefold()
                for filename in _resolve_filename_candidates(asset)
            ):
                continue
            filtered_assets.append(asset)
        return filtered_assets

    def _list_all_assets(self) -> list[_AssetRow]:
        rows = self._session.execute(
            select(
                Asset.id,
                Asset.short_id,
                Asset.source_id,
                Asset.timestamp,
                Asset.media_type,
                Asset.external_id,
                Asset.summary,
                Asset.metadata_json,
                Asset.folder_id,
            ).order_by(Asset.timestamp.desc(), Asset.id.desc())
        )
        return [
            _AssetRow(
                id=asset_id,
                short_id=short_id,
                source_id=source_id,
                timestamp_iso=timestamp.isoformat(),
                media_type=media_type,
                external_id=external_id,
                summary=summary,
                metadata_json=metadata_json if isinstance(metadata_json, dict) else None,
                folder_id=folder_id,
            )
            for (
                asset_id,
                short_id,
                source_id,
                timestamp,
                media_type,
                external_id,
                summary,
                metadata_json,
                folder_id,
            ) in rows
        ]

    def _list_person_links_by_asset(self, *, asset_ids: list[int]) -> dict[int, set[int]]:
        if not asset_ids:
            return {}

        rows = self._session.execute(
            select(AssetPerson.asset_id, Person.id)
            .join(Person, Person.id == AssetPerson.person_id)
            .where(AssetPerson.asset_id.in_(asset_ids))
        )
        links: dict[int, set[int]] = {asset_id: set() for asset_id in asset_ids}
        for asset_id, person_id in rows:
            links.setdefault(asset_id, set()).add(person_id)
        return links

    def _list_tag_links_by_asset(self, *, asset_ids: list[int]) -> dict[int, list[str]]:
        if not asset_ids:
            return {}

        rows = self._session.execute(
            select(AssetTag.asset_id, Tag.path)
            .join(Tag, Tag.id == AssetTag.tag_id)
            .where(
                AssetTag.asset_id.in_(asset_ids),
                Tag.path.is_not(None),
            )
        )
        links: dict[int, list[str]] = {asset_id: [] for asset_id in asset_ids}
        for asset_id, tag_path in rows:
            if isinstance(tag_path, str) and tag_path:
                links.setdefault(asset_id, []).append(tag_path)
        return links

    def _list_collection_memberships_by_asset(
        self,
        *,
        asset_ids: list[int],
    ) -> dict[int, set[int]]:
        if not asset_ids:
            return {}

        rows = self._session.execute(
            select(AssetCollectionItem.asset_id, AssetCollectionItem.collection_id).where(
                AssetCollectionItem.asset_id.in_(asset_ids)
            )
        )
        memberships: dict[int, set[int]] = {asset_id: set() for asset_id in asset_ids}
        for asset_id, collection_id in rows:
            memberships.setdefault(asset_id, set()).add(collection_id)
        return memberships

    def _count_assets_by_folder_subtree(
        self,
        *,
        filters: AlbumQueryFilters,
        nodes: list[_FolderNodeRow],
    ) -> dict[int, int]:
        if not nodes:
            return {}

        nodes_by_id = {node.id: node for node in nodes}
        counts: dict[int, int] = {}
        for asset in self._list_filtered_assets(filters=filters):
            if asset.folder_id is None:
                continue
            node = nodes_by_id.get(asset.folder_id)
            while node is not None:
                counts[node.id] = counts.get(node.id, 0) + 1
                node = nodes_by_id.get(node.parent_id) if node.parent_id is not None else None
        return counts

    def _count_assets_by_collection_subtree(
        self,
        *,
        filters: AlbumQueryFilters,
        nodes: list[_CollectionNodeRow],
    ) -> dict[int, int]:
        if not nodes:
            return {}

        nodes_by_id = {node.id: node for node in nodes}
        counted_assets_by_node_id: dict[int, set[int]] = {}
        memberships_by_asset_id = self._list_collection_memberships_by_asset(
            asset_ids=[asset.id for asset in self._list_filtered_assets(filters=filters)]
        )
        for asset_id, direct_collection_ids in memberships_by_asset_id.items():
            for collection_id in direct_collection_ids:
                node = nodes_by_id.get(collection_id)
                visited_node_ids: set[int] = set()
                while node is not None and node.id not in visited_node_ids:
                    counted_assets_by_node_id.setdefault(node.id, set()).add(asset_id)
                    visited_node_ids.add(node.id)
                    node = (
                        nodes_by_id.get(node.parent_id)
                        if node.parent_id is not None
                        else None
                    )
        return {
            node_id: len(asset_ids)
            for node_id, asset_ids in counted_assets_by_node_id.items()
        }

    def _to_listing_item(self, asset: _AssetRow) -> AlbumAssetListItemSnapshot:
        return AlbumAssetListItemSnapshot(
            id=asset.id,
            short_id=asset.short_id,
            timestamp_iso=asset.timestamp_iso,
            media_type=asset.media_type,
            title=_resolve_asset_title(asset),
        )


def _count_children_by_parent_id(parent_ids: Any) -> dict[int, int]:
    counts: dict[int, int] = {}
    for parent_id in parent_ids:
        if parent_id is None:
            continue
        counts[parent_id] = counts.get(parent_id, 0) + 1
    return counts


def _is_navigation_descendant(*, candidate_path: str, selected_path: str) -> bool:
    return (
        candidate_path == selected_path
        or candidate_path.startswith(f"{selected_path}/")
    )


def _tag_path_matches_selection(
    *,
    asset_tag_path: str,
    selected_tag_path: str,
) -> bool:
    return (
        asset_tag_path == selected_tag_path
        or asset_tag_path.startswith(f"{selected_tag_path}/")
        or selected_tag_path.startswith(f"{asset_tag_path}/")
    )


def _resolve_asset_title(asset: _AssetRow) -> str:
    if isinstance(asset.summary, str) and asset.summary.strip():
        return asset.summary.strip()

    for candidate in _resolve_filename_candidates(asset):
        if candidate:
            return candidate

    return asset.media_type


def _resolve_filename_candidates(asset: _AssetRow) -> tuple[str, ...]:
    metadata = asset.metadata_json if isinstance(asset.metadata_json, dict) else {}
    candidates: list[str] = []
    for key in (
        "preserved_file_name",
        "file_name",
        "filename",
        "original_filename",
        "source_path",
        "file_path",
    ):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            extracted = _extract_filename(value)
            if extracted not in candidates:
                candidates.append(extracted)

    external_name = _extract_filename(asset.external_id)
    if external_name not in candidates:
        candidates.append(external_name)
    return tuple(candidates)


def _extract_filename(value: str) -> str:
    normalized = value.strip().replace("\\", "/")
    if not normalized:
        return ""
    return PurePath(normalized).name or normalized
