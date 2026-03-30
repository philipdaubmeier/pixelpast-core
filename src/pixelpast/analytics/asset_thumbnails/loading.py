"""Canonical asset loading for thumbnail derivation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pixelpast.persistence.repositories import (
    AssetMediaRepository,
    AssetThumbnailCandidate,
)


@dataclass(slots=True, frozen=True)
class ResolvedThumbnailAsset:
    """One canonical asset resolved to a concrete source image path."""

    asset_id: int
    short_id: str
    source_type: str
    media_type: str
    original_path: Path | None


class AssetThumbnailCanonicalLoader:
    """Load canonical asset candidates and resolve their original image paths."""

    def load_assets(
        self,
        *,
        repository: AssetMediaRepository,
    ) -> tuple[ResolvedThumbnailAsset, ...]:
        """Return deterministic thumbnail candidates from canonical assets."""

        return tuple(
            self._resolve_asset(candidate)
            for candidate in repository.list_thumbnail_candidates()
        )

    def _resolve_asset(
        self,
        candidate: AssetThumbnailCandidate,
    ) -> ResolvedThumbnailAsset:
        metadata = candidate.metadata_json or {}
        original_path: Path | None
        if candidate.source_type == "photos":
            original_path = Path(candidate.external_id)
        elif candidate.source_type == "lightroom_catalog":
            file_path = metadata.get("file_path")
            original_path = Path(file_path) if isinstance(file_path, str) else None
        else:
            original_path = None

        return ResolvedThumbnailAsset(
            asset_id=candidate.asset_id,
            short_id=candidate.short_id,
            source_type=candidate.source_type,
            media_type=candidate.media_type,
            original_path=original_path,
        )


__all__ = [
    "AssetThumbnailCanonicalLoader",
    "ResolvedThumbnailAsset",
]
