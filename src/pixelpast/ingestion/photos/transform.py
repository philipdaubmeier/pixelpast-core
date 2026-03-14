"""Pure metadata transformation logic for photo ingestion."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

from pixelpast.ingestion.photos.contracts import (
    PhotoAssetCandidate,
    PhotoPersonCandidate,
)

_FILENAME_TIMESTAMP_PATTERN = re.compile(r"(?P<stamp>\d{8}_\d{6})")
_EXIF_DATETIME_TAG = 36867
_EXIF_FALLBACK_DATETIME_TAG = 306
_EXIF_GPS_TAG = 34853
_HIERARCHY_SEPARATOR = "|"
_TITLE_METADATA_PRIORITY = ("XMP:Title", "XMP-dc:Title", "IPTC:ObjectName")
_CREATOR_METADATA_PRIORITY = (
    "XMP:Creator",
    "XMP-dc:Creator",
    "IPTC:By-line",
    "EXIF:Artist",
    "IFD0:Artist",
)
_TIMESTAMP_METADATA_PRIORITY = ("EXIF:DateTimeOriginal", "ExifIFD:DateTimeOriginal")
_GPS_METADATA_PRIORITY = (
    ("Composite:GPSLatitude", "Composite:GPSLongitude"),
    ("EXIF:GPSLatitude", "EXIF:GPSLongitude"),
    ("GPS:GPSLatitude", "GPS:GPSLongitude"),
)
_EXPLICIT_TAG_METADATA_PRIORITY = ("XMP:Subject", "XMP-dc:Subject", "IPTC:Keywords")
_HIERARCHICAL_TAG_METADATA_PRIORITY = (
    "XMP:HierarchicalSubject",
    "XMP-lr:HierarchicalSubject",
)
_REGION_NAME_KEYS = ("XMP:RegionName", "XMP-mwg-rs:RegionName")
_REGION_TYPE_KEYS = ("XMP:RegionType", "XMP-mwg-rs:RegionType")


@dataclass(slots=True, frozen=True)
class PhotoExifMetadata:
    """Fallback EXIF metadata used when richer metadata extraction is unavailable."""

    timestamp: datetime | None
    latitude: float | None
    longitude: float | None


class PhotoMetadataTransformer:
    """Build canonical photo asset candidates from extracted metadata."""

    def build_asset_candidate(
        self,
        *,
        path: Path,
        metadata: dict[str, Any],
        fallback_exif: PhotoExifMetadata,
    ) -> PhotoAssetCandidate:
        """Build a canonical asset candidate for a single file."""

        title, title_source = _resolve_first_string(
            metadata=metadata,
            keys=_TITLE_METADATA_PRIORITY,
        )
        creator_name, creator_source = _resolve_first_string(
            metadata=metadata,
            keys=_CREATOR_METADATA_PRIORITY,
        )
        timestamp, timestamp_source = _resolve_photo_timestamp(
            path=path,
            metadata=metadata,
            fallback_exif=fallback_exif,
        )
        latitude, longitude, gps_source = _resolve_photo_coordinates(
            metadata=metadata,
            fallback_exif=fallback_exif,
        )

        explicit_labels = _extract_explicit_tag_labels(metadata)
        hierarchical_paths = _extract_hierarchical_paths(metadata)
        hierarchy_node_paths = _expand_hierarchy_paths(hierarchical_paths)
        persons, excluded_tag_paths = _resolve_person_candidates(
            metadata=metadata,
            hierarchical_paths=hierarchical_paths,
        )
        asset_tag_paths = _resolve_asset_tag_paths(
            explicit_labels=explicit_labels,
            hierarchy_node_paths=hierarchy_node_paths,
            excluded_tag_paths=excluded_tag_paths,
        )
        tag_paths = tuple(
            sorted(
                set(hierarchy_node_paths).union(asset_tag_paths),
                key=lambda value: (value.count(_HIERARCHY_SEPARATOR), value),
            )
        )

        metadata_json = _build_metadata_json(
            path=path,
            title=title,
            title_source=title_source,
            creator_name=creator_name,
            creator_source=creator_source,
            timestamp_source=timestamp_source,
            gps_source=gps_source,
            explicit_labels=explicit_labels,
            hierarchical_paths=hierarchical_paths,
            linked_tag_paths=asset_tag_paths,
            persons=persons,
        )

        return PhotoAssetCandidate(
            external_id=path.as_posix(),
            media_type="photo",
            timestamp=timestamp,
            summary=title,
            latitude=latitude,
            longitude=longitude,
            creator_name=creator_name,
            tag_paths=tag_paths,
            asset_tag_paths=asset_tag_paths,
            persons=persons,
            metadata_json=metadata_json,
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


def _resolve_first_string(
    *,
    metadata: dict[str, Any],
    keys: tuple[str, ...],
) -> tuple[str | None, str | None]:
    """Resolve the first non-empty string from an ordered key precedence list."""

    for key in keys:
        candidate = metadata.get(key)
        if isinstance(candidate, str) and candidate != "":
            return candidate, key
    return None, None


def _resolve_photo_timestamp(
    *,
    path: Path,
    metadata: dict[str, Any],
    fallback_exif: PhotoExifMetadata,
) -> tuple[datetime, str]:
    """Resolve the canonical asset timestamp with deterministic fallbacks."""

    for key in _TIMESTAMP_METADATA_PRIORITY:
        metadata_timestamp = _parse_exif_datetime(metadata.get(key))
        if metadata_timestamp is not None:
            return metadata_timestamp, key

    if fallback_exif.timestamp is not None:
        return fallback_exif.timestamp, "fallback_exif"

    filename_timestamp = _parse_filename_timestamp(path.stem)
    if filename_timestamp is not None:
        return filename_timestamp, "filename"

    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC), "mtime"


def _resolve_photo_coordinates(
    *,
    metadata: dict[str, Any],
    fallback_exif: PhotoExifMetadata,
) -> tuple[float | None, float | None, str | None]:
    """Resolve the canonical GPS coordinates from metadata or EXIF fallback."""

    for latitude_key, longitude_key in _GPS_METADATA_PRIORITY:
        latitude = _coerce_float(metadata.get(latitude_key))
        longitude = _coerce_float(metadata.get(longitude_key))
        if latitude is not None and longitude is not None:
            return latitude, longitude, f"{latitude_key},{longitude_key}"

    if fallback_exif.latitude is not None and fallback_exif.longitude is not None:
        return fallback_exif.latitude, fallback_exif.longitude, "fallback_exif"

    return None, None, None


def _extract_explicit_tag_labels(metadata: dict[str, Any]) -> tuple[str, ...]:
    """Return deduplicated explicit keyword labels from XMP/IPTC metadata."""

    ordered_labels: list[str] = []
    seen: set[str] = set()
    for key in _EXPLICIT_TAG_METADATA_PRIORITY:
        for value in _coerce_string_list(metadata.get(key)):
            if value in seen:
                continue
            seen.add(value)
            ordered_labels.append(value)
    return tuple(ordered_labels)


def _extract_hierarchical_paths(metadata: dict[str, Any]) -> tuple[str, ...]:
    """Return normalized hierarchical subject paths in deterministic order."""

    ordered_paths: list[str] = []
    seen: set[str] = set()
    for key in _HIERARCHICAL_TAG_METADATA_PRIORITY:
        for value in _coerce_string_list(metadata.get(key)):
            normalized = _normalize_hierarchy_path(value)
            if normalized is None or normalized in seen:
                continue
            seen.add(normalized)
            ordered_paths.append(normalized)
    return tuple(ordered_paths)


def _expand_hierarchy_paths(hierarchical_paths: tuple[str, ...]) -> tuple[str, ...]:
    """Return all hierarchy nodes required to materialize discovered paths."""

    ordered_paths: list[str] = []
    seen: set[str] = set()
    for path in hierarchical_paths:
        segments = path.split(_HIERARCHY_SEPARATOR)
        for index in range(1, len(segments) + 1):
            candidate = _HIERARCHY_SEPARATOR.join(segments[:index])
            if candidate in seen:
                continue
            seen.add(candidate)
            ordered_paths.append(candidate)
    return tuple(ordered_paths)


def _resolve_person_candidates(
    *,
    metadata: dict[str, Any],
    hierarchical_paths: tuple[str, ...],
) -> tuple[tuple[PhotoPersonCandidate, ...], frozenset[str]]:
    """Resolve face-region persons and match them to canonical hierarchical paths."""

    face_names = _extract_face_region_names(metadata)
    resolved_persons: list[PhotoPersonCandidate] = []
    excluded_tag_paths: set[str] = set()

    for name in face_names:
        matching_path = _resolve_matching_person_path(
            person_name=name,
            hierarchical_paths=hierarchical_paths,
        )
        if matching_path is not None:
            excluded_tag_paths.add(matching_path)
        resolved_persons.append(
            PhotoPersonCandidate(
                name=name,
                path=matching_path,
            )
        )

    return tuple(resolved_persons), frozenset(excluded_tag_paths)


def _extract_face_region_names(metadata: dict[str, Any]) -> tuple[str, ...]:
    """Return deduplicated face-region person names in metadata order."""

    region_names = _resolve_first_string_list(metadata=metadata, keys=_REGION_NAME_KEYS)
    region_types = _resolve_first_string_list(metadata=metadata, keys=_REGION_TYPE_KEYS)
    if not region_names:
        return ()

    if not region_types:
        region_types = ["Face"] * len(region_names)
    elif len(region_types) == 1 and len(region_names) > 1:
        region_types = region_types * len(region_names)

    ordered_names: list[str] = []
    seen: set[str] = set()
    for index, name in enumerate(region_names):
        region_type = region_types[index] if index < len(region_types) else None
        if region_type != "Face" or name in seen:
            continue
        seen.add(name)
        ordered_names.append(name)
    return tuple(ordered_names)


def _resolve_matching_person_path(
    *,
    person_name: str,
    hierarchical_paths: tuple[str, ...],
) -> str | None:
    """Return the most specific hierarchical path whose leaf label matches a person."""

    matches = [
        path
        for path in hierarchical_paths
        if path.rsplit(_HIERARCHY_SEPARATOR, 1)[-1] == person_name
    ]
    if not matches:
        return None
    return sorted(
        matches,
        key=lambda value: (-value.count(_HIERARCHY_SEPARATOR), value),
    )[0]


def _resolve_asset_tag_paths(
    *,
    explicit_labels: tuple[str, ...],
    hierarchy_node_paths: tuple[str, ...],
    excluded_tag_paths: frozenset[str],
) -> tuple[str, ...]:
    """Resolve explicit keywords to canonical tag paths and exclude person tags."""

    linked_paths: list[str] = []
    seen: set[str] = set()

    for label in explicit_labels:
        path = _resolve_explicit_tag_path(
            explicit_label=label,
            hierarchy_node_paths=hierarchy_node_paths,
        )
        if path in excluded_tag_paths or path in seen:
            continue
        seen.add(path)
        linked_paths.append(path)

    return tuple(linked_paths)


def _resolve_explicit_tag_path(
    *,
    explicit_label: str,
    hierarchy_node_paths: tuple[str, ...],
) -> str:
    """Resolve an explicit keyword to the canonical tag path that should be linked."""

    matches = [
        path
        for path in hierarchy_node_paths
        if path.rsplit(_HIERARCHY_SEPARATOR, 1)[-1] == explicit_label
    ]
    if not matches:
        return explicit_label
    return sorted(
        matches,
        key=lambda value: (value.count(_HIERARCHY_SEPARATOR), value),
    )[0]


def _build_metadata_json(
    *,
    path: Path,
    title: str | None,
    title_source: str | None,
    creator_name: str | None,
    creator_source: str | None,
    timestamp_source: str,
    gps_source: str | None,
    explicit_labels: tuple[str, ...],
    hierarchical_paths: tuple[str, ...],
    linked_tag_paths: tuple[str, ...],
    persons: tuple[PhotoPersonCandidate, ...],
) -> dict[str, Any]:
    """Build a compact persistence payload describing metadata resolution."""

    return {
        "source_path": path.as_posix(),
        "resolution": {
            "title": title_source,
            "timestamp": timestamp_source,
            "gps": gps_source,
            "creator": creator_source,
        },
        "title": title,
        "creator_name": creator_name,
        "explicit_keywords": list(explicit_labels),
        "hierarchical_subjects": list(hierarchical_paths),
        "linked_tag_paths": list(linked_tag_paths),
        "persons": [
            {
                "name": person.name,
                "path": person.path,
            }
            for person in persons
        ],
    }


def _normalize_hierarchy_path(value: str) -> str | None:
    """Normalize a hierarchical path while preserving segment text."""

    segments = [
        segment for segment in value.split(_HIERARCHY_SEPARATOR) if segment != ""
    ]
    if not segments:
        return None
    return _HIERARCHY_SEPARATOR.join(segments)


def _coerce_string_list(value: object) -> list[str]:
    """Normalize scalar or list-like metadata values into a list of strings."""

    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _resolve_first_string_list(
    *,
    metadata: dict[str, Any],
    keys: tuple[str, ...],
) -> list[str]:
    """Resolve the first non-empty list-like string metadata value."""

    for key in keys:
        values = _coerce_string_list(metadata.get(key))
        if values:
            return values
    return []


def _coerce_float(value: object) -> float | None:
    """Coerce supported numeric metadata values to float."""

    if isinstance(value, int | float):
        return float(value)
    return None


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


__all__ = [
    "PhotoAssetCandidate",
    "PhotoExifMetadata",
    "PhotoMetadataTransformer",
    "PhotoPersonCandidate",
    "extract_photo_exif_metadata",
]
