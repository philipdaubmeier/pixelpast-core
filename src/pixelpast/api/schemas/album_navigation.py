"""Schemas for album-navigation trees and asset-listing reads."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AlbumAppliedFilters(BaseModel):
    """Explicit supported filter state applied to an album response."""

    person_ids: list[int] = Field(default_factory=list)
    tag_paths: list[str] = Field(default_factory=list)
    filename_query: str | None = None


class AlbumFolderTreeNode(BaseModel):
    """Readable physical folder-tree node for album navigation."""

    id: int
    source_id: int
    source_name: str
    source_type: str
    parent_id: int | None
    name: str
    path: str
    child_count: int
    asset_count: int


class AlbumCollectionTreeNode(BaseModel):
    """Readable semantic collection-tree node for album navigation."""

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


class AlbumFoldersTreeResponse(BaseModel):
    """Read response for the physical album folder tree."""

    supported_filters: list[str]
    applied_filters: AlbumAppliedFilters
    nodes: list[AlbumFolderTreeNode]


class AlbumCollectionsTreeResponse(BaseModel):
    """Read response for the semantic album collection tree."""

    supported_filters: list[str]
    applied_filters: AlbumAppliedFilters
    nodes: list[AlbumCollectionTreeNode]


class AlbumSelection(BaseModel):
    """Selected folder or collection summary for one album listing."""

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


class AlbumAssetItem(BaseModel):
    """Thumbnail-grid asset row exposed by the album listing contract."""

    id: int
    short_id: str
    timestamp: str
    media_type: str
    title: str
    thumbnail_url: str


class AlbumAssetListingResponse(BaseModel):
    """Read response for one selected album subtree asset listing."""

    supported_filters: list[str]
    applied_filters: AlbumAppliedFilters
    selection: AlbumSelection
    items: list[AlbumAssetItem]
