"""Schemas for album-navigation trees and asset-listing reads."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AlbumAppliedFilters(BaseModel):
    """Explicit supported filter state applied to an album response."""

    person_ids: list[int] = Field(default_factory=list)
    person_group_ids: list[int] | None = None
    tag_paths: list[str] = Field(default_factory=list)
    filename_query: str | None = None


class AlbumPersonGroupRelevance(BaseModel):
    """Derived person-group relevance summary for one album node."""

    group_id: int
    group_name: str
    color_index: int | None = None
    matched_person_count: int
    group_person_count: int
    matched_asset_count: int
    matched_creator_person_count: int


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
    person_groups: list[AlbumPersonGroupRelevance] = Field(default_factory=list)


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
    person_groups: list[AlbumPersonGroupRelevance] = Field(default_factory=list)


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


class AlbumAssetPerson(BaseModel):
    """Linked person summary for one selected asset detail payload."""

    id: int
    name: str
    path: str | None


class AlbumAssetTag(BaseModel):
    """Linked tag summary for one selected asset detail payload."""

    id: int
    label: str
    path: str | None


class AlbumContextPerson(BaseModel):
    """Stable person aggregate for one selected album subtree."""

    id: int
    name: str
    path: str | None
    asset_count: int


class AlbumContextTag(BaseModel):
    """Stable tag aggregate for one selected album subtree."""

    id: int
    label: str
    path: str | None
    asset_count: int


class AlbumContextMapPoint(BaseModel):
    """Stable map point aggregate for one selected album subtree."""

    id: str
    label: str | None = None
    latitude: float
    longitude: float
    asset_count: int


class AlbumContextAssetItem(BaseModel):
    """Per-asset lightweight context used for client-side hover highlighting."""

    asset_id: int
    person_ids: list[int] = Field(default_factory=list)
    tag_paths: list[str] = Field(default_factory=list)
    map_point_ids: list[str] = Field(default_factory=list)


class AlbumContextSummaryCounts(BaseModel):
    """Summary counters for one selected album context response."""

    assets: int
    people: int
    tags: int
    places: int


class AlbumContextResponse(BaseModel):
    """Stable right-column context for one selected album subtree."""

    supported_filters: list[str]
    applied_filters: AlbumAppliedFilters
    selection: AlbumSelection
    person_groups: list[AlbumPersonGroupRelevance] = Field(default_factory=list)
    persons: list[AlbumContextPerson] = Field(default_factory=list)
    tags: list[AlbumContextTag] = Field(default_factory=list)
    map_points: list[AlbumContextMapPoint] = Field(default_factory=list)
    asset_contexts: list[AlbumContextAssetItem] = Field(default_factory=list)
    summary_counts: AlbumContextSummaryCounts


class AlbumFaceRegion(BaseModel):
    """Named face rectangle normalized for optional UI overlay rendering."""

    name: str
    left: float
    top: float
    right: float
    bottom: float


class AlbumAssetDetailResponse(BaseModel):
    """Single-photo detail payload kept off the thumbnail-grid hot path."""

    id: int
    short_id: str
    source_id: int
    source_name: str
    source_type: str
    media_type: str
    title: str
    creator: str | None = None
    preserved_filename: str | None = None
    caption: str | None = None
    description: str | None = None
    timestamp: str
    latitude: float | None = None
    longitude: float | None = None
    camera: str | None = None
    lens: str | None = None
    aperture_f_number: float | None = None
    shutter_speed_seconds: float | None = None
    focal_length_mm: float | None = None
    iso: int | float | None = None
    thumbnail_url: str
    original_url: str
    tags: list[AlbumAssetTag] = Field(default_factory=list)
    people: list[AlbumAssetPerson] = Field(default_factory=list)
    face_regions: list[AlbumFaceRegion] = Field(default_factory=list)
