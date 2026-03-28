"""Public data contracts for Lightroom Classic catalog ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True, frozen=True)
class LightroomCatalogDescriptor:
    """One discovered Lightroom Classic catalog file."""

    path: Path

    @property
    def origin_path(self) -> Path:
        """Return the normalized filesystem path for this catalog."""

        return self.path.expanduser().resolve()

    @property
    def origin_label(self) -> str:
        """Return the deterministic human-readable catalog identifier."""

        return self.origin_path.as_posix()


@dataclass(slots=True, frozen=True)
class LightroomChosenImageRow:
    """One chosen Lightroom image row representing a physical file."""

    image_id: int
    root_file_id: int
    file_name: str
    file_path: str
    capture_time_text: str | None
    rating: int | None
    color_label: str | None
    xmp_blob: bytes
    caption: str | None
    creator_name: str | None
    gps_latitude: float | None
    gps_longitude: float | None


@dataclass(slots=True, frozen=True)
class LightroomXmpPayload:
    """One decompressed Lightroom XMP payload for a chosen image row."""

    image_id: int
    xml_text: str
    document_id: str | None
    preserved_file_name: str | None
    title: str | None
    hierarchical_keywords: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class LightroomPersonCandidate:
    """Canonicalized person candidate derived from a Lightroom face name."""

    name: str
    path: str | None


@dataclass(slots=True, frozen=True)
class LightroomFaceRegion:
    """One named Lightroom face rectangle stored in asset metadata."""

    name: str | None
    left: float
    top: float
    right: float
    bottom: float


@dataclass(slots=True, frozen=True)
class LightroomCollectionMembership:
    """One Lightroom collection membership stored in asset metadata."""

    collection_id: int
    path: str
    name: str


@dataclass(slots=True, frozen=True)
class LightroomAssetCandidate:
    """Canonical asset candidate derived from one Lightroom physical file."""

    external_id: str
    media_type: str
    timestamp: datetime
    summary: str | None
    latitude: float | None
    longitude: float | None
    creator_name: str | None
    tag_paths: tuple[str, ...]
    persons: tuple[LightroomPersonCandidate, ...]
    metadata_json: dict[str, Any] | None


@dataclass(slots=True, frozen=True)
class LightroomCatalogCandidate:
    """Transform result for one catalog file that yields many assets."""

    catalog: LightroomCatalogDescriptor
    chosen_images: tuple[LightroomChosenImageRow, ...]
    assets: tuple[LightroomAssetCandidate, ...]


@dataclass(slots=True, frozen=True)
class LightroomTransformError:
    """Represents one non-fatal Lightroom catalog transform failure."""

    catalog: LightroomCatalogDescriptor
    message: str


@dataclass(slots=True, frozen=True)
class LightroomIngestionResult:
    """Summary of a completed Lightroom catalog ingestion run."""

    run_id: int
    processed_catalog_count: int
    processed_asset_count: int
    persisted_asset_count: int
    error_count: int
    status: str
    warning_messages: tuple[str, ...] = ()
    transform_errors: tuple[LightroomTransformError, ...] = ()


__all__ = [
    "LightroomAssetCandidate",
    "LightroomCatalogCandidate",
    "LightroomCatalogDescriptor",
    "LightroomChosenImageRow",
    "LightroomCollectionMembership",
    "LightroomFaceRegion",
    "LightroomIngestionResult",
    "LightroomPersonCandidate",
    "LightroomTransformError",
    "LightroomXmpPayload",
]
