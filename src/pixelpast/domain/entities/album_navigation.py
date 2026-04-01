"""Domain records for album-navigation storage concerns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class AssetFolderRecord:
    """Canonical folder node used for physical asset hierarchy navigation."""

    id: int
    source_id: int
    parent_id: int | None
    name: str
    path: str


@dataclass(slots=True, frozen=True)
class AssetCollectionRecord:
    """Canonical collection node used for semantic album navigation."""

    id: int
    source_id: int
    parent_id: int | None
    name: str
    path: str
    external_id: str
    collection_type: str
    metadata_json: dict[str, Any] | None


@dataclass(slots=True, frozen=True)
class AssetCollectionItemRecord:
    """Canonical membership between one collection and one asset."""

    collection_id: int
    asset_id: int


@dataclass(slots=True, frozen=True)
class AlbumNavigationFillInResult:
    """Summary of one album-navigation fill-in execution."""

    created_folder_count: int
    created_collection_count: int
    assigned_asset_folder_count: int
    linked_collection_item_count: int
    unresolved_asset_count: int
