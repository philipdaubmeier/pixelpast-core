"""Filesystem-based discovery and metadata extraction for photo assets."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

_SUPPORTED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".heic"})
_FILENAME_TIMESTAMP_PATTERN = re.compile(r"(?P<stamp>\d{8}_\d{6})")
_EXIF_DATETIME_TAG = 36867
_EXIF_FALLBACK_DATETIME_TAG = 306
_EXIF_GPS_TAG = 34853


@dataclass(slots=True, frozen=True)
class PhotoExifMetadata:
    """EXIF metadata used for canonical asset extraction."""

    timestamp: datetime | None
    latitude: float | None
    longitude: float | None


@dataclass(slots=True, frozen=True)
class PhotoAssetCandidate:
    """Canonicalized asset candidate discovered from the filesystem."""

    external_id: str
    media_type: str
    timestamp: datetime
    latitude: float | None
    longitude: float | None
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


class PhotoConnector:
    """Discover photo assets recursively from a configured root directory."""

    def discover(self, root: Path) -> PhotoDiscoveryResult:
        """Return canonical asset candidates discovered under a directory tree."""

        resolved_root = root.expanduser().resolve()
        if not resolved_root.exists():
            raise ValueError(f"Photo root does not exist: {resolved_root}")
        if not resolved_root.is_dir():
            raise ValueError(f"Photo root is not a directory: {resolved_root}")

        assets: list[PhotoAssetCandidate] = []
        errors: list[PhotoDiscoveryError] = []

        for path in sorted(resolved_root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in _SUPPORTED_EXTENSIONS:
                continue

            try:
                assets.append(
                    self.build_asset_candidate(root=resolved_root, path=path)
                )
            except Exception as error:
                errors.append(PhotoDiscoveryError(path=path, message=str(error)))

        return PhotoDiscoveryResult(assets=assets, errors=errors)

    def build_asset_candidate(self, *, root: Path, path: Path) -> PhotoAssetCandidate:
        """Build a canonical asset candidate for a single file."""

        resolved_path = path.expanduser().resolve()

        exif_metadata = extract_photo_exif_metadata(resolved_path)
        timestamp, _ = _resolve_photo_timestamp(
            path=resolved_path,
            exif_timestamp=exif_metadata.timestamp,
        )

        return PhotoAssetCandidate(
            external_id=resolved_path.as_posix(),
            media_type="photo",
            timestamp=timestamp,
            latitude=exif_metadata.latitude,
            longitude=exif_metadata.longitude,
            metadata_json={},
        )


def extract_photo_exif_metadata(path: Path) -> PhotoExifMetadata:
    """Extract timestamp and GPS metadata from a photo when readable."""

    try:
        with Image.open(path) as image:
            exif = image.getexif()
    except (FileNotFoundError, OSError, UnidentifiedImageError):
        return PhotoExifMetadata(timestamp=None, latitude=None, longitude=None)

    if not exif:
        return PhotoExifMetadata(timestamp=None, latitude=None, longitude=None)

    timestamp = _parse_exif_datetime(
        exif.get(_EXIF_DATETIME_TAG) or exif.get(_EXIF_FALLBACK_DATETIME_TAG)
    )
    latitude, longitude = _extract_gps_coordinates(exif=exif)
    return PhotoExifMetadata(
        timestamp=timestamp,
        latitude=latitude,
        longitude=longitude,
    )


def _resolve_photo_timestamp(
    *,
    path: Path,
    exif_timestamp: datetime | None,
) -> tuple[datetime, str]:
    """Resolve the canonical asset timestamp with deterministic fallbacks."""

    if exif_timestamp is not None:
        return exif_timestamp, "exif"

    filename_timestamp = _parse_filename_timestamp(path.stem)
    if filename_timestamp is not None:
        return filename_timestamp, "filename"

    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC), "mtime"


def _parse_filename_timestamp(stem: str) -> datetime | None:
    """Parse supported filename timestamp patterns from a file stem."""

    match = _FILENAME_TIMESTAMP_PATTERN.search(stem)
    if match is None:
        return None

    parsed = datetime.strptime(match.group("stamp"), "%Y%m%d_%H%M%S")
    return parsed.replace(tzinfo=UTC)


def _parse_exif_datetime(value: object) -> datetime | None:
    """Parse a supported EXIF date-time value into an aware UTC timestamp."""

    if not isinstance(value, str):
        return None

    try:
        parsed = datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None

    return parsed.replace(tzinfo=UTC)


def _extract_gps_coordinates(*, exif: Any) -> tuple[float | None, float | None]:
    """Extract decimal GPS coordinates from a Pillow EXIF structure."""

    gps_data: dict[int, Any] = {}
    if hasattr(exif, "get_ifd"):
        try:
            gps_data = exif.get_ifd(_EXIF_GPS_TAG) or {}
        except KeyError:
            gps_data = {}
    elif _EXIF_GPS_TAG in exif:
        gps_data = exif.get(_EXIF_GPS_TAG) or {}

    latitude = _parse_gps_coordinate(gps_data.get(2), gps_data.get(1))
    longitude = _parse_gps_coordinate(gps_data.get(4), gps_data.get(3))
    return latitude, longitude


def _parse_gps_coordinate(
    values: object,
    reference: object,
) -> float | None:
    """Convert EXIF GPS rational tuples to signed decimal degrees."""

    if values is None or not isinstance(reference, str):
        return None

    try:
        degrees, minutes, seconds = (float(value) for value in values)
    except (TypeError, ValueError):
        return None

    decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
    if reference.upper() in {"S", "W"}:
        decimal *= -1.0
    return decimal
