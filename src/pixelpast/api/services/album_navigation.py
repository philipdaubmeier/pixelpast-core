"""Service layer for album-navigation API responses."""

from __future__ import annotations

from pixelpast.api.schemas import (
    AlbumAppliedFilters,
    AlbumAssetDetailResponse,
    AlbumAssetItem,
    AlbumAssetListingResponse,
    AlbumAssetPerson,
    AlbumAssetTag,
    AlbumCollectionTreeNode,
    AlbumCollectionsTreeResponse,
    AlbumFaceRegion,
    AlbumFolderTreeNode,
    AlbumFoldersTreeResponse,
    AlbumSelection,
)
from pixelpast.persistence.repositories.album_navigation_read import (
    AlbumAssetDetailSnapshot,
    AlbumAssetListingSnapshot,
    AlbumAssetPersonSnapshot,
    AlbumAssetTagSnapshot,
    AlbumCollectionTreeNodeSnapshot,
    AlbumFaceRegionSnapshot,
    AlbumFolderTreeNodeSnapshot,
    AlbumNavigationReadRepository,
    AlbumQueryFilters,
)

SUPPORTED_ALBUM_FILTERS: tuple[str, ...] = ("person_ids", "tag_paths", "filename_query")


class AlbumNavigationQueryService:
    """Compose album read repositories into explicit REST response models."""

    def __init__(self, *, repository: AlbumNavigationReadRepository) -> None:
        self._repository = repository

    def get_folder_tree(self, *, filters: AlbumQueryFilters) -> AlbumFoldersTreeResponse:
        """Return the filtered physical folder tree."""

        return AlbumFoldersTreeResponse(
            supported_filters=list(SUPPORTED_ALBUM_FILTERS),
            applied_filters=_to_applied_filters(filters),
            nodes=[
                _to_folder_tree_node(node)
                for node in self._repository.list_folder_tree(filters=filters)
            ],
        )

    def get_collection_tree(
        self,
        *,
        filters: AlbumQueryFilters,
    ) -> AlbumCollectionsTreeResponse:
        """Return the filtered semantic collection tree."""

        return AlbumCollectionsTreeResponse(
            supported_filters=list(SUPPORTED_ALBUM_FILTERS),
            applied_filters=_to_applied_filters(filters),
            nodes=[
                _to_collection_tree_node(node)
                for node in self._repository.list_collection_tree(filters=filters)
            ],
        )

    def get_folder_asset_listing(
        self,
        *,
        folder_id: int,
        filters: AlbumQueryFilters,
    ) -> AlbumAssetListingResponse | None:
        """Return the filtered subtree asset listing for one folder."""

        snapshot = self._repository.get_folder_asset_listing(
            folder_id=folder_id,
            filters=filters,
        )
        if snapshot is None:
            return None
        return _to_asset_listing_response(snapshot=snapshot, filters=filters)

    def get_collection_asset_listing(
        self,
        *,
        collection_id: int,
        filters: AlbumQueryFilters,
    ) -> AlbumAssetListingResponse | None:
        """Return the filtered subtree asset listing for one collection."""

        snapshot = self._repository.get_collection_asset_listing(
            collection_id=collection_id,
            filters=filters,
        )
        if snapshot is None:
            return None
        return _to_asset_listing_response(snapshot=snapshot, filters=filters)

    def get_asset_detail(self, *, asset_id: int) -> AlbumAssetDetailResponse | None:
        """Return one normalized single-photo detail payload."""

        snapshot = self._repository.get_asset_detail(asset_id=asset_id)
        if snapshot is None:
            return None
        return _to_asset_detail_response(snapshot)


def _to_applied_filters(filters: AlbumQueryFilters) -> AlbumAppliedFilters:
    return AlbumAppliedFilters(
        person_ids=list(filters.person_ids),
        tag_paths=list(filters.tag_paths),
        filename_query=filters.filename_query,
    )


def _to_folder_tree_node(node: AlbumFolderTreeNodeSnapshot) -> AlbumFolderTreeNode:
    return AlbumFolderTreeNode(
        id=node.id,
        source_id=node.source_id,
        source_name=node.source_name,
        source_type=node.source_type,
        parent_id=node.parent_id,
        name=node.name,
        path=node.path,
        child_count=node.child_count,
        asset_count=node.asset_count,
    )


def _to_collection_tree_node(
    node: AlbumCollectionTreeNodeSnapshot,
) -> AlbumCollectionTreeNode:
    return AlbumCollectionTreeNode(
        id=node.id,
        source_id=node.source_id,
        source_name=node.source_name,
        source_type=node.source_type,
        parent_id=node.parent_id,
        name=node.name,
        path=node.path,
        collection_type=node.collection_type,
        child_count=node.child_count,
        asset_count=node.asset_count,
    )


def _to_asset_listing_response(
    *,
    snapshot: AlbumAssetListingSnapshot,
    filters: AlbumQueryFilters,
) -> AlbumAssetListingResponse:
    return AlbumAssetListingResponse(
        supported_filters=list(SUPPORTED_ALBUM_FILTERS),
        applied_filters=_to_applied_filters(filters),
        selection=AlbumSelection(
            node_kind=snapshot.selection.node_kind,
            id=snapshot.selection.id,
            source_id=snapshot.selection.source_id,
            source_name=snapshot.selection.source_name,
            source_type=snapshot.selection.source_type,
            parent_id=snapshot.selection.parent_id,
            name=snapshot.selection.name,
            path=snapshot.selection.path,
            asset_count=snapshot.selection.asset_count,
            collection_type=snapshot.selection.collection_type,
        ),
        items=[
            AlbumAssetItem(
                id=item.id,
                short_id=item.short_id,
                timestamp=item.timestamp_iso,
                media_type=item.media_type,
                title=item.title,
                thumbnail_url=f"/media/q200/{item.short_id}.webp",
            )
            for item in snapshot.items
        ],
    )


def _to_asset_detail_response(
    snapshot: AlbumAssetDetailSnapshot,
) -> AlbumAssetDetailResponse:
    return AlbumAssetDetailResponse(
        id=snapshot.id,
        short_id=snapshot.short_id,
        source_id=snapshot.source_id,
        source_name=snapshot.source_name,
        source_type=snapshot.source_type,
        media_type=snapshot.media_type,
        title=snapshot.title,
        caption=snapshot.caption,
        description=snapshot.description,
        timestamp=snapshot.timestamp_iso,
        latitude=snapshot.latitude,
        longitude=snapshot.longitude,
        camera=snapshot.camera,
        lens=snapshot.lens,
        aperture_f_number=snapshot.aperture_f_number,
        shutter_speed_seconds=snapshot.shutter_speed_seconds,
        focal_length_mm=snapshot.focal_length_mm,
        iso=snapshot.iso,
        thumbnail_url=f"/media/q200/{snapshot.short_id}.webp",
        original_url=f"/media/orig/{snapshot.short_id}",
        tags=[_to_asset_tag(tag) for tag in snapshot.tags],
        people=[_to_asset_person(person) for person in snapshot.people],
        face_regions=[_to_face_region(region) for region in snapshot.face_regions],
    )


def _to_asset_person(person: AlbumAssetPersonSnapshot) -> AlbumAssetPerson:
    return AlbumAssetPerson(id=person.id, name=person.name, path=person.path)


def _to_asset_tag(tag: AlbumAssetTagSnapshot) -> AlbumAssetTag:
    return AlbumAssetTag(id=tag.id, label=tag.label, path=tag.path)


def _to_face_region(region: AlbumFaceRegionSnapshot) -> AlbumFaceRegion:
    return AlbumFaceRegion(
        name=region.name,
        left=region.left,
        top=region.top,
        right=region.right,
        bottom=region.bottom,
    )
