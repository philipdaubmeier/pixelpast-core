"""Read repositories for album-navigation trees and asset listings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pixelpast.persistence.models import (
    Asset,
    AssetCollection,
    AssetCollectionItem,
    AssetCollectionPersonGroup,
    AssetFolder,
    AssetFolderPersonGroup,
    AssetPerson,
    AssetTag,
    Person,
    PersonGroup,
    PersonGroupMember,
    Source,
    Tag,
)


@dataclass(frozen=True, slots=True)
class AlbumQueryFilters:
    """Normalized supported persistent filters for album reads."""

    person_ids: tuple[int, ...] = ()
    person_group_ids: tuple[int, ...] = ()
    tag_paths: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AlbumPersonGroupRelevanceSnapshot:
    """Serializable derived person-group relevance for one album node."""

    group_id: int
    group_name: str
    color_index: int | None
    matched_person_count: int
    group_person_count: int
    matched_asset_count: int
    matched_creator_person_count: int


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
    person_groups: tuple[AlbumPersonGroupRelevanceSnapshot, ...]


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
    person_groups: tuple[AlbumPersonGroupRelevanceSnapshot, ...]


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
class AlbumPageSnapshot:
    """Serializable page metadata for paged album selection reads."""

    offset: int
    limit: int
    returned: int
    total: int


@dataclass(frozen=True, slots=True)
class AlbumAssetListingSnapshot:
    """Serializable album asset-list response body."""

    selection: AlbumSelectionSnapshot
    page: AlbumPageSnapshot
    items: tuple[AlbumAssetListItemSnapshot, ...]


@dataclass(frozen=True, slots=True)
class AlbumAssetPersonSnapshot:
    """Serializable linked person summary for one asset detail payload."""

    id: int
    name: str
    path: str | None


@dataclass(frozen=True, slots=True)
class AlbumAssetTagSnapshot:
    """Serializable linked tag summary for one asset detail payload."""

    id: int
    label: str
    path: str | None


@dataclass(frozen=True, slots=True)
class AlbumContextPersonSnapshot:
    """Serializable person aggregate for one selected album subtree."""

    id: int
    name: str
    path: str | None
    asset_count: int


@dataclass(frozen=True, slots=True)
class AlbumContextTagSnapshot:
    """Serializable tag aggregate for one selected album subtree."""

    id: int
    label: str
    path: str | None
    asset_count: int


@dataclass(frozen=True, slots=True)
class AlbumContextMapPointSnapshot:
    """Serializable map point aggregate for one selected album subtree."""

    id: str
    label: str | None
    latitude: float
    longitude: float
    asset_count: int


@dataclass(frozen=True, slots=True)
class AlbumContextAssetSnapshot:
    """Serializable per-asset hover context for one album listing item."""

    asset_id: int
    person_ids: tuple[int, ...]
    tag_paths: tuple[str, ...]
    map_point_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AlbumContextSummarySnapshot:
    """Serializable summary counts for one selected album subtree."""

    assets: int
    people: int
    tags: int
    places: int


@dataclass(frozen=True, slots=True)
class AlbumContextSnapshot:
    """Serializable stable album context for one selected folder or collection."""

    selection: AlbumSelectionSnapshot
    person_groups: tuple[AlbumPersonGroupRelevanceSnapshot, ...]
    persons: tuple[AlbumContextPersonSnapshot, ...]
    tags: tuple[AlbumContextTagSnapshot, ...]
    map_points: tuple[AlbumContextMapPointSnapshot, ...]
    summary_counts: AlbumContextSummarySnapshot


@dataclass(frozen=True, slots=True)
class AlbumAssetContextPageSnapshot:
    """Serializable page-scoped per-asset hover context payload."""

    selection: AlbumSelectionSnapshot
    page: AlbumPageSnapshot
    asset_contexts: tuple[AlbumContextAssetSnapshot, ...]


@dataclass(frozen=True, slots=True)
class AlbumFaceRegionSnapshot:
    """Serializable normalized named face region for one asset detail payload."""

    name: str
    left: float
    top: float
    right: float
    bottom: float


@dataclass(frozen=True, slots=True)
class AlbumAssetDetailSnapshot:
    """Serializable single-asset photo detail snapshot."""

    id: int
    short_id: str
    source_id: int
    source_name: str
    source_type: str
    media_type: str
    title: str
    creator: str | None
    preserved_filename: str | None
    caption: str | None
    description: str | None
    timestamp_iso: str
    latitude: float | None
    longitude: float | None
    camera: str | None
    lens: str | None
    aperture_f_number: float | None
    shutter_speed_seconds: float | None
    focal_length_mm: float | None
    iso: int | float | None
    people: tuple[AlbumAssetPersonSnapshot, ...]
    tags: tuple[AlbumAssetTagSnapshot, ...]
    face_regions: tuple[AlbumFaceRegionSnapshot, ...]


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
    latitude: float | None
    longitude: float | None
    external_id: str
    summary: str | None
    metadata_json: dict[str, Any] | None
    folder_id: int | None


@dataclass(frozen=True, slots=True)
class _AssetDetailRow:
    id: int
    short_id: str
    source_id: int
    source_name: str
    source_type: str
    media_type: str
    timestamp_iso: str
    summary: str | None
    latitude: float | None
    longitude: float | None
    external_id: str
    creator_name: str | None
    metadata_json: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class _PageSlice:
    offset: int
    limit: int
    items: tuple[_AssetRow, ...]


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
        person_groups_by_folder_id = self._list_folder_person_groups_by_node_id()
        counts = self._count_assets_by_folder_subtree(nodes=nodes)
        if filters.person_group_ids:
            counts = self._count_assets_by_folder_subtree_for_person_groups(
                nodes=nodes,
                person_group_ids=filters.person_group_ids,
            )
            nodes = [
                node
                for node in nodes
                if any(
                    group.group_id in filters.person_group_ids
                    for group in person_groups_by_folder_id.get(node.id, ())
                )
            ]
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
                person_groups=person_groups_by_folder_id.get(node.id, ()),
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
        person_groups_by_collection_id = self._list_collection_person_groups_by_node_id()
        counts = self._count_assets_by_collection_subtree(nodes=nodes)
        if filters.person_group_ids:
            counts = self._count_assets_by_collection_subtree_for_person_groups(
                nodes=nodes,
                person_group_ids=filters.person_group_ids,
            )
            nodes = [
                node
                for node in nodes
                if any(
                    group.group_id in filters.person_group_ids
                    for group in person_groups_by_collection_id.get(node.id, ())
                )
            ]
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
                person_groups=person_groups_by_collection_id.get(node.id, ()),
            )
            for node in ordered_nodes
        )

    def get_folder_asset_listing(
        self,
        *,
        folder_id: int,
        filters: AlbumQueryFilters,
        offset: int,
        limit: int,
    ) -> AlbumAssetListingSnapshot | None:
        """Return the filtered asset listing for one folder subtree selection."""

        selection_assets = self._get_folder_selection_assets(
            folder_id=folder_id,
            filters=filters,
        )
        if selection_assets is None:
            return None
        selection, selected_assets = selection_assets
        page = _slice_page(items=selected_assets, offset=offset, limit=limit)
        return AlbumAssetListingSnapshot(
            selection=selection,
            page=AlbumPageSnapshot(
                offset=page.offset,
                limit=page.limit,
                returned=len(page.items),
                total=len(selected_assets),
            ),
            items=tuple(self._to_listing_item(asset) for asset in page.items),
        )

    def get_collection_asset_listing(
        self,
        *,
        collection_id: int,
        filters: AlbumQueryFilters,
        offset: int,
        limit: int,
    ) -> AlbumAssetListingSnapshot | None:
        """Return the filtered asset listing for one collection subtree selection."""

        selection_assets = self._get_collection_selection_assets(
            collection_id=collection_id,
            filters=filters,
        )
        if selection_assets is None:
            return None
        selection, selected_assets = selection_assets
        page = _slice_page(items=selected_assets, offset=offset, limit=limit)
        return AlbumAssetListingSnapshot(
            selection=selection,
            page=AlbumPageSnapshot(
                offset=page.offset,
                limit=page.limit,
                returned=len(page.items),
                total=len(selected_assets),
            ),
            items=tuple(self._to_listing_item(asset) for asset in page.items),
        )

    def get_folder_asset_context_page(
        self,
        *,
        folder_id: int,
        filters: AlbumQueryFilters,
        offset: int,
        limit: int,
    ) -> AlbumAssetContextPageSnapshot | None:
        """Return page-local hover context for one folder subtree selection."""

        selection_assets = self._get_folder_selection_assets(
            folder_id=folder_id,
            filters=filters,
        )
        if selection_assets is None:
            return None
        selection, selected_assets = selection_assets
        page = _slice_page(items=selected_assets, offset=offset, limit=limit)
        return self._build_asset_context_page_snapshot(
            selection=selection,
            assets=tuple(page.items),
            total_asset_count=len(selected_assets),
            offset=page.offset,
            limit=page.limit,
        )

    def get_collection_asset_context_page(
        self,
        *,
        collection_id: int,
        filters: AlbumQueryFilters,
        offset: int,
        limit: int,
    ) -> AlbumAssetContextPageSnapshot | None:
        """Return page-local hover context for one collection subtree selection."""

        selection_assets = self._get_collection_selection_assets(
            collection_id=collection_id,
            filters=filters,
        )
        if selection_assets is None:
            return None
        selection, selected_assets = selection_assets
        page = _slice_page(items=selected_assets, offset=offset, limit=limit)
        return self._build_asset_context_page_snapshot(
            selection=selection,
            assets=tuple(page.items),
            total_asset_count=len(selected_assets),
            offset=page.offset,
            limit=page.limit,
        )

    def get_folder_context(
        self,
        *,
        folder_id: int,
        filters: AlbumQueryFilters,
    ) -> AlbumContextSnapshot | None:
        """Return the stable context for one selected folder subtree."""

        listing = self.get_folder_asset_listing(
            folder_id=folder_id,
            filters=filters,
            offset=0,
            limit=2**31 - 1,
        )
        if listing is None:
            return None
        return self._build_context_snapshot(
            selection=listing.selection,
            assets=tuple(self._list_assets_by_selection(listing=listing)),
            person_groups=self._list_person_groups_for_folder(folder_id=folder_id),
        )

    def get_collection_context(
        self,
        *,
        collection_id: int,
        filters: AlbumQueryFilters,
    ) -> AlbumContextSnapshot | None:
        """Return the stable context for one selected collection subtree."""

        listing = self.get_collection_asset_listing(
            collection_id=collection_id,
            filters=filters,
            offset=0,
            limit=2**31 - 1,
        )
        if listing is None:
            return None
        return self._build_context_snapshot(
            selection=listing.selection,
            assets=tuple(self._list_assets_by_selection(listing=listing)),
            person_groups=self._list_person_groups_for_collection(collection_id=collection_id),
        )

    def get_asset_detail(self, *, asset_id: int) -> AlbumAssetDetailSnapshot | None:
        """Return one normalized single-photo detail snapshot by canonical asset id."""

        row = self._session.execute(
            select(
                Asset.id,
                Asset.short_id,
                Asset.source_id,
                Source.name,
                Source.type,
                Asset.media_type,
                Asset.timestamp,
                Asset.summary,
                Asset.latitude,
                Asset.longitude,
                Asset.external_id,
                Person.name,
                Asset.metadata_json,
            )
            .join(Source, Source.id == Asset.source_id)
            .outerjoin(Person, Person.id == Asset.creator_person_id)
            .where(Asset.id == asset_id)
        ).one_or_none()
        if row is None:
            return None

        detail_row = _AssetDetailRow(
            id=row[0],
            short_id=row[1],
            source_id=row[2],
            source_name=row[3],
            source_type=row[4],
            media_type=row[5],
            timestamp_iso=row[6].isoformat(),
            summary=row[7],
            latitude=row[8],
            longitude=row[9],
            external_id=row[10],
            creator_name=row[11] if isinstance(row[11], str) else None,
            metadata_json=row[12] if isinstance(row[12], dict) else None,
        )
        metadata = detail_row.metadata_json if isinstance(detail_row.metadata_json, dict) else {}

        return AlbumAssetDetailSnapshot(
            id=detail_row.id,
            short_id=detail_row.short_id,
            source_id=detail_row.source_id,
            source_name=detail_row.source_name,
            source_type=detail_row.source_type,
            media_type=detail_row.media_type,
            title=_resolve_asset_detail_title(detail_row),
            creator=detail_row.creator_name,
            preserved_filename=_resolve_metadata_text(
                metadata,
                "preserved_filename",
                "preserved_file_name",
            ),
            caption=_resolve_metadata_text(metadata, "caption"),
            description=_resolve_metadata_text(metadata, "description", "comment"),
            timestamp_iso=detail_row.timestamp_iso,
            latitude=detail_row.latitude,
            longitude=detail_row.longitude,
            camera=_resolve_metadata_text(metadata, "camera"),
            lens=_resolve_metadata_text(metadata, "lens"),
            aperture_f_number=_resolve_metadata_float(metadata, "aperture_f_number"),
            shutter_speed_seconds=_resolve_metadata_float(
                metadata,
                "shutter_speed_seconds",
            ),
            focal_length_mm=_resolve_metadata_float(
                metadata,
                "focal_length_mm",
                "focal_length",
            ),
            iso=_resolve_metadata_number(metadata, "iso"),
            people=self._list_asset_people(asset_id=detail_row.id),
            tags=self._list_asset_tags(asset_id=detail_row.id),
            face_regions=_resolve_face_regions(metadata),
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

    def _list_folder_person_groups_by_node_id(
        self,
    ) -> dict[int, tuple[AlbumPersonGroupRelevanceSnapshot, ...]]:
        rows = self._session.execute(
            select(
                AssetFolderPersonGroup.folder_id,
                PersonGroup.id,
                PersonGroup.name,
                PersonGroup.metadata_json,
                AssetFolderPersonGroup.matched_person_count,
                AssetFolderPersonGroup.group_person_count,
                AssetFolderPersonGroup.matched_asset_count,
                AssetFolderPersonGroup.matched_creator_person_count,
            )
            .join(PersonGroup, PersonGroup.id == AssetFolderPersonGroup.group_id)
            .order_by(
                AssetFolderPersonGroup.folder_id,
                AssetFolderPersonGroup.matched_person_count.desc(),
                AssetFolderPersonGroup.matched_asset_count.desc(),
                func.lower(PersonGroup.name),
                PersonGroup.id,
            )
        )
        grouped_rows: dict[int, list[AlbumPersonGroupRelevanceSnapshot]] = {}
        for (
            folder_id,
            group_id,
            group_name,
            metadata_json,
            matched_person_count,
            group_person_count,
            matched_asset_count,
            matched_creator_person_count,
        ) in rows:
            grouped_rows.setdefault(folder_id, []).append(
                AlbumPersonGroupRelevanceSnapshot(
                    group_id=group_id,
                    group_name=group_name,
                    color_index=_normalize_person_group_color_index(metadata_json),
                    matched_person_count=matched_person_count,
                    group_person_count=group_person_count,
                    matched_asset_count=matched_asset_count,
                    matched_creator_person_count=matched_creator_person_count,
                )
            )
        return {
            folder_id: tuple(group_rows)
            for folder_id, group_rows in grouped_rows.items()
        }

    def _list_collection_person_groups_by_node_id(
        self,
    ) -> dict[int, tuple[AlbumPersonGroupRelevanceSnapshot, ...]]:
        rows = self._session.execute(
            select(
                AssetCollectionPersonGroup.collection_id,
                PersonGroup.id,
                PersonGroup.name,
                PersonGroup.metadata_json,
                AssetCollectionPersonGroup.matched_person_count,
                AssetCollectionPersonGroup.group_person_count,
                AssetCollectionPersonGroup.matched_asset_count,
                AssetCollectionPersonGroup.matched_creator_person_count,
            )
            .join(PersonGroup, PersonGroup.id == AssetCollectionPersonGroup.group_id)
            .order_by(
                AssetCollectionPersonGroup.collection_id,
                AssetCollectionPersonGroup.matched_person_count.desc(),
                AssetCollectionPersonGroup.matched_asset_count.desc(),
                func.lower(PersonGroup.name),
                PersonGroup.id,
            )
        )
        grouped_rows: dict[int, list[AlbumPersonGroupRelevanceSnapshot]] = {}
        for (
            collection_id,
            group_id,
            group_name,
            metadata_json,
            matched_person_count,
            group_person_count,
            matched_asset_count,
            matched_creator_person_count,
        ) in rows:
            grouped_rows.setdefault(collection_id, []).append(
                AlbumPersonGroupRelevanceSnapshot(
                    group_id=group_id,
                    group_name=group_name,
                    color_index=_normalize_person_group_color_index(metadata_json),
                    matched_person_count=matched_person_count,
                    group_person_count=group_person_count,
                    matched_asset_count=matched_asset_count,
                    matched_creator_person_count=matched_creator_person_count,
                )
            )
        return {
            collection_id: tuple(group_rows)
            for collection_id, group_rows in grouped_rows.items()
        }

    def _list_person_groups_for_folder(
        self,
        *,
        folder_id: int,
    ) -> tuple[AlbumPersonGroupRelevanceSnapshot, ...]:
        return self._list_folder_person_groups_by_node_id().get(folder_id, ())

    def _list_person_groups_for_collection(
        self,
        *,
        collection_id: int,
    ) -> tuple[AlbumPersonGroupRelevanceSnapshot, ...]:
        return self._list_collection_person_groups_by_node_id().get(collection_id, ())

    def _get_folder_selection_assets(
        self,
        *,
        folder_id: int,
        filters: AlbumQueryFilters,
    ) -> tuple[AlbumSelectionSnapshot, list[_AssetRow]] | None:
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
        selected_assets = self._filter_assets(
            assets=self._list_assets_for_folder_ids(folder_ids=descendant_ids),
            filters=filters,
        )
        return (
            AlbumSelectionSnapshot(
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
            selected_assets,
        )

    def _get_collection_selection_assets(
        self,
        *,
        collection_id: int,
        filters: AlbumQueryFilters,
    ) -> tuple[AlbumSelectionSnapshot, list[_AssetRow]] | None:
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
        selected_assets = self._filter_assets(
            assets=self._list_assets_for_collection_ids(
                collection_ids=descendant_collection_ids
            ),
            filters=filters,
        )
        return (
            AlbumSelectionSnapshot(
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
            selected_assets,
        )

    def _filter_assets(
        self,
        *,
        assets: list[_AssetRow],
        filters: AlbumQueryFilters,
    ) -> list[_AssetRow]:
        if not assets:
            return []

        asset_ids = [asset.id for asset in assets]
        person_links_by_asset: dict[int, set[int]] = {}
        if filters.person_ids:
            person_links_by_asset = self._list_person_links_by_asset(asset_ids=asset_ids)

        tag_links_by_asset: dict[int, list[str]] = {}
        if filters.tag_paths:
            tag_links_by_asset = self._list_tag_links_by_asset(asset_ids=asset_ids)

        filtered_assets: list[_AssetRow] = []
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
            filtered_assets.append(asset)
        return filtered_assets

    def _list_assets(
        self,
        statement,
    ) -> list[_AssetRow]:
        rows = self._session.execute(
            statement.order_by(Asset.timestamp.desc(), Asset.id.desc())
        )
        return [
            _AssetRow(
                id=asset_id,
                short_id=short_id,
                source_id=source_id,
                timestamp_iso=timestamp.isoformat(),
                media_type=media_type,
                latitude=latitude,
                longitude=longitude,
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
                latitude,
                longitude,
                external_id,
                summary,
                metadata_json,
                folder_id,
            ) in rows
        ]

    def _base_asset_select(self):
        return select(
            Asset.id,
            Asset.short_id,
            Asset.source_id,
            Asset.timestamp,
            Asset.media_type,
            Asset.latitude,
            Asset.longitude,
            Asset.external_id,
            Asset.summary,
            Asset.metadata_json,
            Asset.folder_id,
        )

    def _list_assets_for_folder_ids(self, *, folder_ids: set[int]) -> list[_AssetRow]:
        if not folder_ids:
            return []
        return self._list_assets(
            self._base_asset_select().where(Asset.folder_id.in_(sorted(folder_ids)))
        )

    def _list_assets_for_collection_ids(
        self,
        *,
        collection_ids: set[int],
    ) -> list[_AssetRow]:
        if not collection_ids:
            return []
        return self._list_assets(
            self._base_asset_select()
            .join(AssetCollectionItem, AssetCollectionItem.asset_id == Asset.id)
            .where(AssetCollectionItem.collection_id.in_(sorted(collection_ids)))
            .distinct()
        )

    def _list_assets_by_ids(self, *, asset_ids: list[int]) -> list[_AssetRow]:
        if not asset_ids:
            return []
        return self._list_assets(self._base_asset_select().where(Asset.id.in_(asset_ids)))

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

    def _matching_person_group_asset_ids_subquery(
        self,
        *,
        person_group_ids: tuple[int, ...],
    ):
        if not person_group_ids:
            return None

        selected_group_ids = sorted(set(person_group_ids))
        person_asset_ids = select(AssetPerson.asset_id).join(
            PersonGroupMember,
            PersonGroupMember.person_id == AssetPerson.person_id,
        ).where(PersonGroupMember.group_id.in_(selected_group_ids))
        creator_asset_ids = select(Asset.id).join(
            PersonGroupMember,
            PersonGroupMember.person_id == Asset.creator_person_id,
        ).where(PersonGroupMember.group_id.in_(selected_group_ids))
        return (
            person_asset_ids.union(creator_asset_ids).subquery()
        )

    def _count_assets_by_folder_subtree(
        self,
        *,
        nodes: list[_FolderNodeRow],
    ) -> dict[int, int]:
        if not nodes:
            return {}

        nodes_by_id = {node.id: node for node in nodes}
        counts: dict[int, int] = {}
        rows = self._session.execute(select(Asset.folder_id).where(Asset.folder_id.is_not(None)))
        for (folder_id,) in rows:
            if folder_id is None:
                continue
            asset_folder_node = nodes_by_id.get(folder_id)
            node = asset_folder_node
            if node is None:
                continue
            while node is not None:
                counts[node.id] = counts.get(node.id, 0) + 1
                node = nodes_by_id.get(node.parent_id) if node.parent_id is not None else None
        return counts

    def _count_assets_by_folder_subtree_for_person_groups(
        self,
        *,
        nodes: list[_FolderNodeRow],
        person_group_ids: tuple[int, ...],
    ) -> dict[int, int]:
        if not nodes or not person_group_ids:
            return {}

        nodes_by_id = {node.id: node for node in nodes}
        matching_asset_ids = self._matching_person_group_asset_ids_subquery(
            person_group_ids=person_group_ids
        )
        if matching_asset_ids is None:
            return {}

        counts: dict[int, int] = {}
        rows = self._session.execute(
            select(Asset.folder_id)
            .join(matching_asset_ids, matching_asset_ids.c.asset_id == Asset.id)
            .where(
                Asset.folder_id.is_not(None),
            )
        )
        for (folder_id,) in rows:
            if folder_id is None:
                continue
            node = nodes_by_id.get(folder_id)
            while node is not None:
                counts[node.id] = counts.get(node.id, 0) + 1
                node = nodes_by_id.get(node.parent_id) if node.parent_id is not None else None
        return counts

    def _count_assets_by_collection_subtree(
        self,
        *,
        nodes: list[_CollectionNodeRow],
    ) -> dict[int, int]:
        if not nodes:
            return {}

        nodes_by_id = {node.id: node for node in nodes}
        counted_assets_by_node_id: dict[int, set[int]] = {}
        memberships_by_asset_id = self._list_collection_memberships_by_asset(
            asset_ids=[
                asset_id
                for (asset_id,) in self._session.execute(select(Asset.id))
            ]
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

    def _count_assets_by_collection_subtree_for_person_groups(
        self,
        *,
        nodes: list[_CollectionNodeRow],
        person_group_ids: tuple[int, ...],
    ) -> dict[int, int]:
        if not nodes or not person_group_ids:
            return {}

        nodes_by_id = {node.id: node for node in nodes}
        matching_asset_ids = self._matching_person_group_asset_ids_subquery(
            person_group_ids=person_group_ids
        )
        if matching_asset_ids is None:
            return {}

        counted_assets_by_node_id: dict[int, set[int]] = {}
        memberships_by_asset_id: dict[int, set[int]] = {}
        rows = self._session.execute(
            select(AssetCollectionItem.asset_id, AssetCollectionItem.collection_id)
            .join(matching_asset_ids, matching_asset_ids.c.asset_id == AssetCollectionItem.asset_id)
        )
        for asset_id, collection_id in rows:
            memberships_by_asset_id.setdefault(asset_id, set()).add(collection_id)

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

    def _build_context_snapshot(
        self,
        *,
        selection: AlbumSelectionSnapshot,
        assets: tuple[_AssetRow, ...],
        person_groups: tuple[AlbumPersonGroupRelevanceSnapshot, ...],
    ) -> AlbumContextSnapshot:
        asset_ids = [asset.id for asset in assets]
        person_links_by_asset = self._list_person_links_by_asset(asset_ids=asset_ids)
        tag_links_by_asset = self._list_tag_links_by_asset(asset_ids=asset_ids)
        persons = self._list_context_people(
            asset_ids=asset_ids,
            person_links_by_asset=person_links_by_asset,
        )
        tags = self._list_context_tags(
            asset_ids=asset_ids,
            tag_links_by_asset=tag_links_by_asset,
        )
        map_points, map_point_ids_by_asset = self._list_context_map_points(assets=assets)
        return AlbumContextSnapshot(
            selection=selection,
            person_groups=person_groups,
            persons=persons,
            tags=tags,
            map_points=map_points,
            summary_counts=AlbumContextSummarySnapshot(
                assets=len(assets),
                people=len(persons),
                tags=len(tags),
                places=len(map_points),
            ),
        )

    def _build_asset_context_page_snapshot(
        self,
        *,
        selection: AlbumSelectionSnapshot,
        assets: tuple[_AssetRow, ...],
        total_asset_count: int,
        offset: int,
        limit: int,
    ) -> AlbumAssetContextPageSnapshot:
        asset_ids = [asset.id for asset in assets]
        person_links_by_asset = self._list_person_links_by_asset(asset_ids=asset_ids)
        tag_links_by_asset = self._list_tag_links_by_asset(asset_ids=asset_ids)
        _, map_point_ids_by_asset = self._list_context_map_points(assets=assets)
        return AlbumAssetContextPageSnapshot(
            selection=selection,
            page=AlbumPageSnapshot(
                offset=offset,
                limit=limit,
                returned=len(assets),
                total=total_asset_count,
            ),
            asset_contexts=tuple(
                AlbumContextAssetSnapshot(
                    asset_id=asset.id,
                    person_ids=tuple(sorted(person_links_by_asset.get(asset.id, set()))),
                    tag_paths=tuple(sorted(tag_links_by_asset.get(asset.id, []))),
                    map_point_ids=map_point_ids_by_asset.get(asset.id, ()),
                )
                for asset in assets
            ),
        )

    def _list_assets_by_selection(
        self,
        listing: AlbumAssetListingSnapshot,
    ) -> list[_AssetRow]:
        if listing.page.total == 0:
            return []
        return self._list_assets_by_ids(
            asset_ids=[
                item.id
                for item in listing.items
            ]
        )

    def _list_context_people(
        self,
        *,
        asset_ids: list[int],
        person_links_by_asset: dict[int, set[int]],
    ) -> tuple[AlbumContextPersonSnapshot, ...]:
        if not asset_ids:
            return ()

        counts_by_person_id: dict[int, int] = {}
        for person_ids in person_links_by_asset.values():
            for person_id in person_ids:
                counts_by_person_id[person_id] = counts_by_person_id.get(person_id, 0) + 1

        if not counts_by_person_id:
            return ()

        rows = self._session.execute(
            select(Person.id, Person.name, Person.path).where(
                Person.id.in_(list(counts_by_person_id))
            )
        )
        return tuple(
            sorted(
                (
                    AlbumContextPersonSnapshot(
                        id=person_id,
                        name=name,
                        path=path,
                        asset_count=counts_by_person_id.get(person_id, 0),
                    )
                    for person_id, name, path in rows
                ),
                key=lambda item: (-item.asset_count, item.name.casefold(), item.path or "", item.id),
            )
        )

    def _list_context_tags(
        self,
        *,
        asset_ids: list[int],
        tag_links_by_asset: dict[int, list[str]],
    ) -> tuple[AlbumContextTagSnapshot, ...]:
        if not asset_ids:
            return ()

        counts_by_tag_path: dict[str, int] = {}
        for asset_tag_paths in tag_links_by_asset.values():
            for tag_path in set(asset_tag_paths):
                counts_by_tag_path[tag_path] = counts_by_tag_path.get(tag_path, 0) + 1

        if not counts_by_tag_path:
            return ()

        rows = self._session.execute(
            select(Tag.id, Tag.label, Tag.path).where(Tag.path.in_(list(counts_by_tag_path)))
        )
        return tuple(
            sorted(
                (
                    AlbumContextTagSnapshot(
                        id=tag_id,
                        label=label,
                        path=path,
                        asset_count=counts_by_tag_path.get(path, 0) if isinstance(path, str) else 0,
                    )
                    for tag_id, label, path in rows
                    if isinstance(path, str) and path
                ),
                key=lambda item: (-item.asset_count, item.path or item.label.casefold(), item.id),
            )
        )

    def _list_context_map_points(
        self,
        *,
        assets: tuple[_AssetRow, ...],
    ) -> tuple[
        tuple[AlbumContextMapPointSnapshot, ...],
        dict[int, tuple[str, ...]],
    ]:
        map_points: list[AlbumContextMapPointSnapshot] = []
        map_point_ids_by_asset: dict[int, tuple[str, ...]] = {}
        for asset in assets:
            metadata = asset.metadata_json if isinstance(asset.metadata_json, dict) else {}
            point_id = f"asset:{asset.short_id}"
            latitude = asset.latitude
            longitude = asset.longitude
            if latitude is None or longitude is None:
                continue
            map_points.append(
                AlbumContextMapPointSnapshot(
                    id=point_id,
                    label=_resolve_metadata_text(metadata, "place_label", "location_label"),
                    latitude=latitude,
                    longitude=longitude,
                    asset_count=1,
                )
            )
            map_point_ids_by_asset[asset.id] = (point_id,)
        return (
            tuple(
                sorted(
                    map_points,
                    key=lambda item: (
                        item.label or "",
                        item.latitude,
                        item.longitude,
                        item.id,
                    ),
                )
            ),
            map_point_ids_by_asset,
        )

    def _list_asset_people(self, *, asset_id: int) -> tuple[AlbumAssetPersonSnapshot, ...]:
        rows = self._session.execute(
            select(Person.id, Person.name, Person.path)
            .join(AssetPerson, AssetPerson.person_id == Person.id)
            .where(AssetPerson.asset_id == asset_id)
        )
        ordered = sorted(
            (
                AlbumAssetPersonSnapshot(id=person_id, name=name, path=path)
                for person_id, name, path in rows
            ),
            key=lambda item: (item.name.casefold(), item.path or "", item.id),
        )
        return tuple(ordered)

    def _list_asset_tags(self, *, asset_id: int) -> tuple[AlbumAssetTagSnapshot, ...]:
        rows = self._session.execute(
            select(Tag.id, Tag.label, Tag.path)
            .join(AssetTag, AssetTag.tag_id == Tag.id)
            .where(AssetTag.asset_id == asset_id)
        )
        ordered = sorted(
            (
                AlbumAssetTagSnapshot(id=tag_id, label=label, path=path)
                for tag_id, label, path in rows
            ),
            key=lambda item: (item.path or item.label.casefold(), item.label.casefold(), item.id),
        )
        return tuple(ordered)


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
    return _resolve_title_value(
        summary=asset.summary,
        metadata=asset.metadata_json,
        external_id=asset.external_id,
        media_type=asset.media_type,
    )


def _resolve_asset_detail_title(asset: _AssetDetailRow) -> str:
    metadata = asset.metadata_json if isinstance(asset.metadata_json, dict) else {}
    metadata_title = _resolve_metadata_text(metadata, "title", "headline")
    if metadata_title is not None:
        return metadata_title
    return _resolve_title_value(
        summary=asset.summary,
        metadata=metadata,
        external_id=asset.external_id,
        media_type=asset.media_type,
    )


def _resolve_title_value(
    *,
    summary: str | None,
    metadata: dict[str, Any] | None,
    external_id: str,
    media_type: str,
) -> str:
    if isinstance(summary, str) and summary.strip():
        return summary.strip()

    for candidate in _resolve_filename_candidates_from_metadata(
        metadata=metadata,
        external_id=external_id,
    ):
        if candidate:
            return candidate

    return media_type


def _resolve_filename_candidates_from_metadata(
    *,
    metadata: dict[str, Any] | None,
    external_id: str,
) -> tuple[str, ...]:
    normalized_metadata = metadata if isinstance(metadata, dict) else {}
    candidates: list[str] = []
    for key in (
        "file_name",
        "preserved_filename",
        "preserved_file_name",
        "filename",
        "original_filename",
        "source_path",
        "file_path",
    ):
        value = normalized_metadata.get(key)
        if isinstance(value, str) and value.strip():
            extracted = _extract_filename(value)
            if extracted not in candidates:
                candidates.append(extracted)

    external_name = _extract_filename(external_id)
    if external_name not in candidates:
        candidates.append(external_name)
    return tuple(candidates)


def _resolve_metadata_text(metadata: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = metadata.get(key)
        if isinstance(value, str):
            normalized = value.strip()
            if normalized:
                return normalized
    return None


def _resolve_metadata_float(metadata: dict[str, Any], *keys: str) -> float | None:
    value = _resolve_metadata_number(metadata, *keys)
    if value is None:
        return None
    return float(value)


def _resolve_metadata_number(
    metadata: dict[str, Any],
    *keys: str,
) -> int | float | None:
    for key in keys:
        value = metadata.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int | float):
            return value
    return None


def _resolve_face_regions(
    metadata: dict[str, Any],
) -> tuple[AlbumFaceRegionSnapshot, ...]:
    raw_regions = metadata.get("face_regions")
    if not isinstance(raw_regions, list):
        return ()

    normalized_regions: list[AlbumFaceRegionSnapshot] = []
    for raw_region in raw_regions:
        if not isinstance(raw_region, dict) or not _is_confirmed_named_face_region(raw_region):
            continue

        name = _resolve_metadata_text(raw_region, "name")
        left = _resolve_metadata_float(raw_region, "left")
        top = _resolve_metadata_float(raw_region, "top")
        right = _resolve_metadata_float(raw_region, "right")
        bottom = _resolve_metadata_float(raw_region, "bottom")
        if name is None or None in {left, top, right, bottom}:
            continue
        normalized_regions.append(
            AlbumFaceRegionSnapshot(
                name=name,
                left=left,
                top=top,
                right=right,
                bottom=bottom,
            )
        )

    return tuple(
        sorted(
            normalized_regions,
            key=lambda item: (
                item.name.casefold(),
                item.left,
                item.top,
                item.right,
                item.bottom,
            ),
        )
    )


def _is_confirmed_named_face_region(region: dict[str, Any]) -> bool:
    if _resolve_metadata_text(region, "name") is None:
        return False
    for rejected_key in ("confirmed", "is_confirmed", "is_named"):
        value = region.get(rejected_key)
        if value is False:
            return False
    status = _resolve_metadata_text(region, "status")
    if status is not None and status.casefold() in {"rejected", "unconfirmed", "unnamed"}:
        return False
    return True


def _extract_filename(value: str) -> str:
    normalized = value.strip().replace("\\", "/")
    if not normalized:
        return ""
    return PurePath(normalized).name or normalized


def _slice_page(*, items: list[_AssetRow], offset: int, limit: int) -> _PageSlice:
    normalized_offset = max(offset, 0)
    normalized_limit = max(limit, 0)
    return _PageSlice(
        offset=normalized_offset,
        limit=normalized_limit,
        items=tuple(items[normalized_offset : normalized_offset + normalized_limit]),
    )


def _normalize_person_group_color_index(metadata_json: Any) -> int | None:
    if not isinstance(metadata_json, dict):
        return None
    ui_metadata = metadata_json.get("ui")
    if not isinstance(ui_metadata, dict):
        return None
    color_index = ui_metadata.get("color_index")
    if (
        not isinstance(color_index, int)
        or isinstance(color_index, bool)
        or color_index <= 0
    ):
        return None
    return color_index
