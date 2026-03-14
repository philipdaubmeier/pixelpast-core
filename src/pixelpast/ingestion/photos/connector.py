"""Composition facade for photo file discovery, metadata fetch, and transform."""

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
from pixelpast.ingestion.photos.discovery import PhotoFileDiscoverer
from pixelpast.ingestion.photos.fetch import (
    PhotoMetadataFetcher,
    count_photo_metadata_batches,
)
from pixelpast.ingestion.photos.transform import (
    PhotoExifMetadata,
    PhotoMetadataTransformer,
    extract_photo_exif_metadata,
)


class PhotoConnector:
    """Facade that composes photo discovery, fetch, and transform stages."""

    def __init__(
        self,
        *,
        file_discoverer: PhotoFileDiscoverer | None = None,
        metadata_fetcher: PhotoMetadataFetcher | None = None,
        metadata_transformer: PhotoMetadataTransformer | None = None,
    ) -> None:
        self._file_discoverer = (
            file_discoverer if file_discoverer is not None else PhotoFileDiscoverer()
        )
        self._metadata_fetcher = (
            metadata_fetcher if metadata_fetcher is not None else PhotoMetadataFetcher()
        )
        self._metadata_transformer = (
            metadata_transformer
            if metadata_transformer is not None
            else PhotoMetadataTransformer()
        )

    def discover_paths(
        self,
        root: Path,
        *,
        on_path_discovered: Callable[[Path, int], None] | None = None,
    ) -> list[Path]:
        """Delegate filesystem discovery to the dedicated discoverer component."""

        return self._file_discoverer.discover_paths(
            root,
            on_path_discovered=on_path_discovered,
        )

    def discover(self, root: Path) -> PhotoDiscoveryResult:
        """Convenience wrapper that runs discover, fetch, and transform together."""

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
