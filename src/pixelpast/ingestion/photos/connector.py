"""Filesystem-based discovery and metadata fetch facade for photo assets."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from pixelpast.ingestion.photos.contracts import (
    PhotoAssetCandidate,
    PhotoDiscoveryError,
    PhotoDiscoveryResult,
    PhotoMetadataBatchProgress,
    PhotoPersonCandidate,
)
from pixelpast.ingestion.photos.fetch import (
    PhotoMetadataFetcher,
    count_photo_metadata_batches,
)
from pixelpast.ingestion.photos.transform import (
    PhotoExifMetadata,
    PhotoMetadataTransformer,
    extract_photo_exif_metadata,
)

_SUPPORTED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".heic"})


class PhotoConnector:
    """Discover photo assets recursively from a configured root directory."""

    def __init__(self, *, metadata_fetcher: PhotoMetadataFetcher | None = None) -> None:
        self._metadata_fetcher = (
            metadata_fetcher if metadata_fetcher is not None else PhotoMetadataFetcher()
        )
        self._metadata_transformer = PhotoMetadataTransformer()

    def discover_paths(
        self,
        root: Path,
        *,
        on_path_discovered: Callable[[Path, int], None] | None = None,
    ) -> list[Path]:
        """Return supported file paths beneath a configured root directory."""

        resolved_root = root.expanduser().resolve()
        if not resolved_root.exists():
            raise ValueError(f"Photo root does not exist: {resolved_root}")
        if not resolved_root.is_dir():
            raise ValueError(f"Photo root is not a directory: {resolved_root}")

        supported_paths: list[Path] = []
        for path in sorted(resolved_root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in _SUPPORTED_EXTENSIONS:
                continue
            supported_paths.append(path)
            if on_path_discovered is not None:
                on_path_discovered(path, len(supported_paths))
        return supported_paths

    def discover(self, root: Path) -> PhotoDiscoveryResult:
        """Return canonical asset candidates discovered under a directory tree."""

        resolved_root = root.expanduser().resolve()
        assets: list[PhotoAssetCandidate] = []
        errors: list[PhotoDiscoveryError] = []
        supported_paths = self.discover_paths(resolved_root)
        metadata_batch_count = count_photo_metadata_batches(len(supported_paths))
        metadata_by_path = self.extract_metadata_by_path(paths=supported_paths)

        for path in supported_paths:
            try:
                assets.append(
                    self.build_asset_candidate(
                        root=resolved_root,
                        path=path,
                        metadata=metadata_by_path.get(path.resolve().as_posix(), {}),
                    )
                )
            except Exception as error:
                errors.append(PhotoDiscoveryError(path=path, message=str(error)))

        return PhotoDiscoveryResult(
            assets=assets,
            errors=errors,
            discovered_paths=tuple(supported_paths),
            metadata_batch_count=metadata_batch_count,
        )

    def build_asset_candidate(
        self,
        *,
        root: Path,
        path: Path,
        metadata: dict[str, Any] | None = None,
    ) -> PhotoAssetCandidate:
        """Build a canonical asset candidate for a single file."""

        del root

        resolved_path = path.expanduser().resolve()
        fallback_exif = extract_photo_exif_metadata(resolved_path)
        resolved_metadata = metadata
        if resolved_metadata is None:
            resolved_metadata = extract_photo_tool_metadata(resolved_path)
        return self._metadata_transformer.build_asset_candidate(
            path=resolved_path,
            metadata=resolved_metadata,
            fallback_exif=fallback_exif,
        )

    def extract_metadata_by_path(
        self,
        *,
        paths: list[Path],
        on_batch_progress: Callable[[PhotoMetadataBatchProgress], None] | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Read grouped metadata for many files through the fetch layer."""

        return self._metadata_fetcher.extract_metadata_by_path(
            paths=paths,
            on_batch_progress=on_batch_progress,
        )


def extract_photo_tool_metadata(path: Path) -> dict[str, Any]:
    """Extract grouped EXIF, IPTC and XMP metadata from a single file."""

    connector = PhotoConnector()
    metadata_by_path = connector.extract_metadata_by_path(paths=[path])
    return metadata_by_path.get(path.expanduser().resolve().as_posix(), {})


__all__ = [
    "PhotoAssetCandidate",
    "PhotoConnector",
    "PhotoDiscoveryError",
    "PhotoDiscoveryResult",
    "PhotoExifMetadata",
    "PhotoMetadataBatchProgress",
    "PhotoPersonCandidate",
    "extract_photo_exif_metadata",
    "extract_photo_tool_metadata",
]
