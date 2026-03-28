"""Pure Lightroom catalog transformation from loaded rows to asset candidates."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from math import pow
from pathlib import Path

from pixelpast.ingestion.lightroom_catalog.contracts import (
    LoadedLightroomCatalog,
    LightroomAssetCandidate,
    LightroomCatalogCandidate,
    LightroomChosenImageRow,
    LightroomCollectionRow,
    LightroomFaceRow,
    LightroomPersonCandidate,
)
from pixelpast.ingestion.lightroom_catalog.xmp import parse_lightroom_xmp_payload

_HIERARCHY_SEPARATOR = "|"
_PHOTO_EXTENSIONS = {
    ".arw",
    ".cr2",
    ".cr3",
    ".dng",
    ".gif",
    ".heic",
    ".jpeg",
    ".jpg",
    ".nef",
    ".orf",
    ".png",
    ".raf",
    ".rw2",
    ".tif",
    ".tiff",
    ".webp",
}
_VIDEO_EXTENSIONS = {
    ".avi",
    ".m4v",
    ".mov",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".mts",
    ".mxf",
    ".wmv",
}


class LightroomCatalogTransformer:
    """Build canonical Lightroom asset candidates from loaded catalog rows."""

    def build_catalog_candidate(
        self,
        catalog: LoadedLightroomCatalog,
    ) -> LightroomCatalogCandidate:
        """Transform one loaded Lightroom catalog into canonical asset candidates."""

        face_rows_by_image: dict[int, list[LightroomFaceRow]] = defaultdict(list)
        for row in catalog.face_rows:
            face_rows_by_image[row.image_id].append(row)

        collection_rows_by_image: dict[int, list[LightroomCollectionRow]] = defaultdict(
            list
        )
        for row in catalog.collection_rows:
            collection_rows_by_image[row.image_id].append(row)

        assets = tuple(
            self.build_asset_candidate(
                image_row=image_row,
                face_rows=face_rows_by_image.get(image_row.image_id, ()),
                collection_rows=collection_rows_by_image.get(image_row.image_id, ()),
            )
            for image_row in catalog.chosen_images
        )
        return LightroomCatalogCandidate(
            catalog=catalog.descriptor,
            chosen_images=catalog.chosen_images,
            assets=assets,
        )

    def build_asset_candidate(
        self,
        *,
        image_row: LightroomChosenImageRow,
        face_rows: Iterable[LightroomFaceRow],
        collection_rows: Iterable[LightroomCollectionRow],
    ) -> LightroomAssetCandidate:
        """Transform one chosen Lightroom image row into one canonical asset."""

        xmp_payload = parse_lightroom_xmp_payload(
            image_id=image_row.image_id,
            blob=image_row.xmp_blob,
        )
        if xmp_payload.document_id is None:
            raise ValueError(
                f"Lightroom image {image_row.image_id} is missing XMP DocumentID."
            )

        timestamp = _parse_capture_timestamp(image_row.capture_time_text)
        hierarchical_keywords = _extract_hierarchical_keywords(
            xmp_payload.hierarchical_keywords
        )
        tag_paths = _expand_hierarchy_paths(hierarchical_keywords)
        persons, excluded_person_paths = _build_person_candidates(
            face_rows=tuple(face_rows),
            tag_paths=tag_paths,
        )
        asset_tag_paths = tuple(
            path for path in tag_paths if path not in excluded_person_paths
        )

        return LightroomAssetCandidate(
            external_id=xmp_payload.document_id,
            media_type=_resolve_media_type(image_row.file_name),
            timestamp=timestamp,
            summary=xmp_payload.title,
            latitude=image_row.gps_latitude,
            longitude=image_row.gps_longitude,
            creator_name=_normalize_optional_text(image_row.creator_name),
            tag_paths=tag_paths,
            asset_tag_paths=asset_tag_paths,
            persons=persons,
            metadata_json={
                "file_name": image_row.file_name,
                "file_path": image_row.file_path,
                "preserved_file_name": xmp_payload.preserved_file_name,
                "caption": _normalize_optional_text(image_row.caption),
                "camera": _normalize_optional_text(image_row.camera),
                "lens": _normalize_optional_text(image_row.lens),
                "aperture_f_number": _convert_aperture_apex(
                    image_row.aperture_apex
                ),
                "shutter_speed_seconds": _convert_shutter_speed_apex(
                    image_row.shutter_speed_apex
                ),
                "iso": _normalize_iso(image_row.iso_speed_rating),
                "rating": image_row.rating,
                "color_label": _normalize_optional_text(image_row.color_label),
                "collections": _build_collection_metadata(collection_rows),
                "face_regions": _build_face_region_metadata(face_rows),
            },
        )


def _parse_capture_timestamp(value: str | None) -> datetime:
    if value is None:
        raise ValueError("Lightroom image is missing captureTime.")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"Unsupported Lightroom captureTime value: {value!r}") from error
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _resolve_media_type(file_name: str) -> str:
    suffix = Path(file_name).suffix.lower()
    if suffix in _VIDEO_EXTENSIONS:
        return "video"
    if suffix in _PHOTO_EXTENSIONS:
        return "photo"
    return "photo"


def _extract_hierarchical_keywords(keywords: tuple[str, ...]) -> tuple[str, ...]:
    ordered_paths: list[str] = []
    seen: set[str] = set()
    for keyword in keywords:
        normalized = _normalize_hierarchical_path(keyword)
        if normalized is None or normalized in seen:
            continue
        seen.add(normalized)
        ordered_paths.append(normalized)
    return tuple(ordered_paths)


def _normalize_hierarchical_path(value: str) -> str | None:
    segments = [segment.strip() for segment in value.split(_HIERARCHY_SEPARATOR)]
    normalized_segments = [segment for segment in segments if segment]
    if not normalized_segments:
        return None
    return _HIERARCHY_SEPARATOR.join(normalized_segments)


def _expand_hierarchy_paths(paths: tuple[str, ...]) -> tuple[str, ...]:
    expanded_paths: list[str] = []
    seen: set[str] = set()
    for path in paths:
        segments = path.split(_HIERARCHY_SEPARATOR)
        for index in range(1, len(segments) + 1):
            candidate = _HIERARCHY_SEPARATOR.join(segments[:index])
            if candidate in seen:
                continue
            seen.add(candidate)
            expanded_paths.append(candidate)
    return tuple(expanded_paths)


def _build_person_candidates(
    *,
    face_rows: tuple[LightroomFaceRow, ...],
    tag_paths: tuple[str, ...],
) -> tuple[tuple[LightroomPersonCandidate, ...], frozenset[str]]:
    persons: list[LightroomPersonCandidate] = []
    excluded_paths: set[str] = set()
    seen_names: set[str] = set()

    for face_row in face_rows:
        name = _normalize_optional_text(face_row.name)
        if name is None or name in seen_names:
            continue
        seen_names.add(name)
        matching_path = _resolve_matching_person_path(name=name, tag_paths=tag_paths)
        if matching_path is not None:
            excluded_paths.add(matching_path)
        persons.append(LightroomPersonCandidate(name=name, path=matching_path))

    return (
        tuple(sorted(persons, key=lambda person: (person.name.casefold(), person.path or ""))),
        frozenset(excluded_paths),
    )


def _resolve_matching_person_path(*, name: str, tag_paths: tuple[str, ...]) -> str | None:
    matches = [
        path for path in tag_paths if path.rsplit(_HIERARCHY_SEPARATOR, 1)[-1] == name
    ]
    if not matches:
        return None
    return sorted(matches, key=lambda value: (-value.count(_HIERARCHY_SEPARATOR), value))[0]


def _build_collection_metadata(
    collection_rows: Iterable[LightroomCollectionRow],
) -> list[dict[str, int | str]]:
    return [
        {
            "id": row.collection_id,
            "name": row.collection_name,
            "path": row.collection_path,
        }
        for row in sorted(
            collection_rows,
            key=lambda row: (row.collection_path.casefold(), row.collection_id),
        )
    ]


def _build_face_region_metadata(
    face_rows: Iterable[LightroomFaceRow],
) -> list[dict[str, float | str | None]]:
    return [
        {
            "name": _normalize_optional_text(row.name),
            "left": row.left,
            "top": row.top,
            "right": row.right,
            "bottom": row.bottom,
        }
        for row in sorted(face_rows, key=lambda row: (row.face_id, row.name or ""))
    ]


def _convert_aperture_apex(value: float | None) -> float | None:
    if value is None:
        return None
    return round(pow(2.0, value / 2.0), 4)


def _convert_shutter_speed_apex(value: float | None) -> float | None:
    if value is None:
        return None
    return round(pow(2.0, -value), 8)


def _normalize_iso(value: float | None) -> int | float | None:
    if value is None:
        return None
    if float(value).is_integer():
        return int(value)
    return float(value)


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if normalized == "":
        return None
    return normalized


__all__ = ["LightroomCatalogTransformer"]
