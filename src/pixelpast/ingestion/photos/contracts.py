"""Public data contracts for photo ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from pixelpast.ingestion.progress import IngestionProgressSnapshot


@dataclass(slots=True, frozen=True)
class PhotoPersonCandidate:
    """Canonicalized person candidate extracted from photo metadata."""

    name: str
    path: str | None


@dataclass(slots=True, frozen=True)
class PhotoAssetCandidate:
    """Canonicalized asset candidate discovered from the filesystem."""

    external_id: str
    media_type: str
    timestamp: datetime
    summary: str | None
    latitude: float | None
    longitude: float | None
    creator_name: str | None
    tag_paths: tuple[str, ...]
    asset_tag_paths: tuple[str, ...]
    persons: tuple[PhotoPersonCandidate, ...]
    metadata_json: dict[str, Any] | None


@dataclass(slots=True, frozen=True)
class PhotoDiscoveryError:
    """Represents a non-fatal discovery or extraction failure."""

    path: Path
    message: str


@dataclass(slots=True, frozen=True)
class PhotoDiscoveryResult:
    """Collection of discovered photo assets and non-fatal issues."""

    assets: list[PhotoAssetCandidate]
    errors: list[PhotoDiscoveryError]
    discovered_paths: tuple[Path, ...] = ()
    metadata_batch_count: int = 0


@dataclass(slots=True, frozen=True)
class PhotoMetadataBatchProgress:
    """Represents one metadata extraction batch transition."""

    event: str
    batch_index: int
    batch_total: int
    batch_size: int


@dataclass(slots=True, frozen=True)
class PhotoIngestionResult:
    """Summary of a completed photo ingestion run."""

    import_run_id: int
    processed_asset_count: int
    error_count: int
    status: str
    discovered_file_count: int
    analyzed_file_count: int
    analysis_failed_file_count: int
    assets_persisted: int
    inserted_asset_count: int
    updated_asset_count: int
    unchanged_asset_count: int
    skipped_asset_count: int
    missing_from_source_count: int
    metadata_batches_submitted: int
    metadata_batches_completed: int


PhotoIngestionProgressSnapshot = IngestionProgressSnapshot


__all__ = [
    "PhotoAssetCandidate",
    "PhotoDiscoveryError",
    "PhotoDiscoveryResult",
    "PhotoIngestionProgressSnapshot",
    "PhotoIngestionResult",
    "PhotoMetadataBatchProgress",
    "PhotoPersonCandidate",
]
