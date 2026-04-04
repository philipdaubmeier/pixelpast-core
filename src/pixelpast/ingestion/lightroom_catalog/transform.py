"""Pure Lightroom catalog transformation from loaded rows to asset candidates."""

from __future__ import annotations

from calendar import isleap
from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from math import pow
from pathlib import Path, PurePosixPath

from pixelpast.ingestion.lightroom_catalog.contracts import (
    LoadedLightroomCatalog,
    LightroomAssetCandidate,
    LightroomCatalogCandidate,
    LightroomChosenImageRow,
    LightroomCollectionMembership,
    LightroomCollectionRow,
    LightroomFaceRow,
    LightroomKeywordRow,
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
        *,
        start_index: int | None = None,
        end_index: int | None = None,
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

        keyword_rows_by_image: dict[int, list[LightroomKeywordRow]] = defaultdict(list)
        for row in catalog.keyword_rows:
            keyword_rows_by_image[row.image_id].append(row)

        selected_image_rows = _slice_image_rows(
            image_rows=catalog.chosen_images,
            start_index=start_index,
            end_index=end_index,
        )
        assets: list[LightroomAssetCandidate] = []
        warning_messages: list[str] = []
        for image_row in selected_image_rows:
            asset_candidate, asset_warning_messages = self.build_asset_candidate(
                image_row=image_row,
                face_rows=face_rows_by_image.get(image_row.image_id, ()),
                keyword_rows=keyword_rows_by_image.get(image_row.image_id, ()),
                collection_rows=collection_rows_by_image.get(image_row.image_id, ()),
            )
            assets.append(asset_candidate)
            warning_messages.extend(asset_warning_messages)
        return LightroomCatalogCandidate(
            catalog=catalog.descriptor,
            chosen_images=selected_image_rows,
            collections=catalog.collection_nodes,
            assets=tuple(assets),
            warning_messages=tuple(warning_messages),
        )

    def build_asset_candidate(
        self,
        *,
        image_row: LightroomChosenImageRow,
        face_rows: Iterable[LightroomFaceRow],
        keyword_rows: Iterable[LightroomKeywordRow],
        collection_rows: Iterable[LightroomCollectionRow],
    ) -> tuple[LightroomAssetCandidate, tuple[str, ...]]:
        """Transform one chosen Lightroom image row into one canonical asset."""

        xmp_payload = parse_lightroom_xmp_payload(
            image_id=image_row.image_id,
            blob=image_row.xmp_blob,
        )
        if xmp_payload.document_id is None:
            raise ValueError(
                f"Lightroom image {image_row.image_id} is missing XMP DocumentID."
            )

        timestamp, timestamp_warning = _parse_capture_timestamp(
            image_row.capture_time_text,
            external_id=xmp_payload.document_id,
        )
        hierarchical_keywords = _extract_hierarchical_keywords(
            xmp_payload.hierarchical_keywords
        )
        explicit_keywords = _extract_explicit_keywords(xmp_payload.explicit_keywords)
        tag_paths = _expand_hierarchy_paths(hierarchical_keywords)
        persons, excluded_person_paths = _build_person_candidates(
            keyword_rows=tuple(keyword_rows),
            face_rows=tuple(face_rows),
            tag_paths=tag_paths,
        )
        asset_tag_paths = _resolve_asset_tag_paths(
            explicit_labels=explicit_keywords,
            hierarchy_node_paths=tag_paths,
            excluded_tag_paths=excluded_person_paths,
        )
        persisted_tag_paths = _resolve_persisted_tag_paths(
            hierarchy_node_paths=tag_paths,
            asset_tag_paths=asset_tag_paths,
            excluded_person_paths=excluded_person_paths,
        )

        return (
            LightroomAssetCandidate(
                external_id=xmp_payload.document_id,
                media_type=_resolve_media_type(image_row.file_name),
                timestamp=timestamp,
                summary=xmp_payload.title,
                latitude=image_row.gps_latitude,
                longitude=image_row.gps_longitude,
                creator_name=_normalize_optional_text(image_row.creator_name),
                tag_paths=tuple(
                    sorted(
                        persisted_tag_paths,
                        key=lambda value: (value.count(_HIERARCHY_SEPARATOR), value),
                    )
                ),
                asset_tag_paths=asset_tag_paths,
                persons=persons,
                folder_path=_build_folder_path(image_row.file_path),
                collections=_build_collection_memberships(collection_rows),
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
                    "explicit_keywords": list(explicit_keywords),
                    "hierarchical_subjects": list(hierarchical_keywords),
                    "linked_tag_paths": list(asset_tag_paths),
                    "collections": _build_collection_metadata(collection_rows),
                    "face_regions": _build_face_region_metadata(face_rows),
                },
            ),
            ((timestamp_warning,) if timestamp_warning is not None else ()),
        )


def _parse_capture_timestamp(
    value: str | None,
    *,
    external_id: str,
) -> tuple[datetime, str | None]:
    if value is None:
        raise ValueError("Lightroom image is missing captureTime.")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        remapped_value = _remap_invalid_leap_day_capture_time(value)
        if remapped_value is None:
            raise ValueError(
                f"Unsupported Lightroom captureTime value: {value!r}"
            ) from error
        parsed = datetime.fromisoformat(remapped_value)
        warning_message = (
            "Lightroom captureTime remapped for asset "
            f"'{external_id}': {value} -> {remapped_value}"
        )
    else:
        warning_message = None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC), warning_message
    return parsed.astimezone(UTC), warning_message


def _remap_invalid_leap_day_capture_time(value: str) -> str | None:
    """Map non-leap-year Feb 29 timestamps to April 1 of the same year."""

    if len(value) < 10:
        return None
    date_part = value[:10]
    time_part = value[10:]
    segments = date_part.split("-")
    if len(segments) != 3:
        return None
    try:
        year = int(segments[0])
        month = int(segments[1])
        day = int(segments[2])
    except ValueError:
        return None
    if month != 2 or day != 29 or isleap(year):
        return None
    return f"{year:04d}-04-01{time_part}"


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
    return _prune_redundant_suffix_paths(tuple(ordered_paths))


def _extract_explicit_keywords(keywords: tuple[str, ...]) -> tuple[str, ...]:
    ordered_labels: list[str] = []
    seen: set[str] = set()
    for keyword in keywords:
        normalized = _normalize_optional_text(keyword)
        if normalized is None or normalized in seen:
            continue
        seen.add(normalized)
        ordered_labels.append(normalized)
    return tuple(ordered_labels)


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
    keyword_rows: tuple[LightroomKeywordRow, ...],
    face_rows: tuple[LightroomFaceRow, ...],
    tag_paths: tuple[str, ...],
) -> tuple[tuple[LightroomPersonCandidate, ...], frozenset[str]]:
    persons: list[LightroomPersonCandidate] = []
    excluded_paths: set[str] = set()
    seen_names: set[str] = set()

    face_names = {
        name
        for face_row in face_rows
        if (name := _normalize_optional_text(face_row.name)) is not None
    }
    for keyword_row in keyword_rows:
        if keyword_row.keyword_type != "person":
            continue
        name = _normalize_optional_text(keyword_row.keyword_name)
        if name is None or name in seen_names:
            continue
        if face_names and name not in face_names:
            continue
        seen_names.add(name)
        matching_path = _resolve_matching_person_path(
            name=name,
            preferred_path=keyword_row.keyword_path,
            tag_paths=tag_paths,
        )
        if matching_path is not None:
            excluded_paths.add(matching_path)
        persons.append(LightroomPersonCandidate(name=name, path=matching_path))

    for name in sorted(face_names, key=str.casefold):
        if name in seen_names:
            continue
        seen_names.add(name)
        matching_path = _resolve_matching_person_path(
            name=name,
            preferred_path=None,
            tag_paths=tag_paths,
        )
        if matching_path is not None:
            excluded_paths.add(matching_path)
        persons.append(LightroomPersonCandidate(name=name, path=matching_path))

    return (
        tuple(sorted(persons, key=lambda person: (person.name.casefold(), person.path or ""))),
        frozenset(excluded_paths),
    )


def _resolve_matching_person_path(
    *,
    name: str,
    preferred_path: str | None,
    tag_paths: tuple[str, ...],
) -> str | None:
    matches = [
        path for path in tag_paths if path.rsplit(_HIERARCHY_SEPARATOR, 1)[-1] == name
    ]
    if not matches:
        return None
    if preferred_path is not None and preferred_path in matches:
        return preferred_path
    return sorted(matches, key=lambda value: (-value.count(_HIERARCHY_SEPARATOR), value))[0]


def _resolve_asset_tag_paths(
    *,
    explicit_labels: tuple[str, ...],
    hierarchy_node_paths: tuple[str, ...],
    excluded_tag_paths: frozenset[str],
) -> tuple[str, ...]:
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


def _resolve_persisted_tag_paths(
    *,
    hierarchy_node_paths: tuple[str, ...],
    asset_tag_paths: tuple[str, ...],
    excluded_person_paths: frozenset[str],
) -> set[str]:
    excluded_hierarchy_nodes = _expand_excluded_hierarchy_nodes(excluded_person_paths)
    return {
        path
        for path in set(hierarchy_node_paths).union(asset_tag_paths)
        if path not in excluded_hierarchy_nodes
    }


def _expand_excluded_hierarchy_nodes(paths: frozenset[str]) -> frozenset[str]:
    excluded_nodes: set[str] = set()
    for path in paths:
        segments = path.split(_HIERARCHY_SEPARATOR)
        for index in range(1, len(segments) + 1):
            excluded_nodes.add(_HIERARCHY_SEPARATOR.join(segments[:index]))
    return frozenset(excluded_nodes)


def _resolve_explicit_tag_path(
    *,
    explicit_label: str,
    hierarchy_node_paths: tuple[str, ...],
) -> str:
    matches = [
        path
        for path in hierarchy_node_paths
        if path.rsplit(_HIERARCHY_SEPARATOR, 1)[-1] == explicit_label
    ]
    if not matches:
        return explicit_label
    return sorted(matches, key=lambda value: (-value.count(_HIERARCHY_SEPARATOR), value))[0]


def _prune_redundant_suffix_paths(paths: tuple[str, ...]) -> tuple[str, ...]:
    pruned_paths: list[str] = []
    for path in paths:
        path_segments = path.split(_HIERARCHY_SEPARATOR)
        if any(
            other != path
            and len(other.split(_HIERARCHY_SEPARATOR)) > len(path_segments)
            and other.split(_HIERARCHY_SEPARATOR)[-len(path_segments) :] == path_segments
            for other in paths
        ):
            continue
        pruned_paths.append(path)
    return tuple(pruned_paths)


def _build_collection_metadata(
    collection_rows: Iterable[LightroomCollectionRow],
) -> list[dict[str, int | str]]:
    memberships = _build_collection_memberships(collection_rows)
    return [
        {
            "id": membership.collection_id,
            "name": membership.name,
            "path": membership.path,
        }
        for membership in memberships
    ]


def _build_collection_memberships(
    collection_rows: Iterable[LightroomCollectionRow],
) -> tuple[LightroomCollectionMembership, ...]:
    return tuple(
        LightroomCollectionMembership(
            collection_id=row.collection_id,
            name=row.collection_name,
            path=row.collection_path,
            collection_type=row.collection_type,
        )
        for row in sorted(
            collection_rows,
            key=lambda row: (row.collection_path.casefold(), row.collection_id),
        )
    )


def _build_folder_path(file_path: str) -> str | None:
    normalized = file_path.strip().replace("\\", "/")
    if normalized == "":
        return None
    parent = PurePosixPath(normalized).parent
    if parent.as_posix() in {"", "."}:
        return None
    return parent.as_posix()


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


def _slice_image_rows(
    *,
    image_rows: tuple[LightroomChosenImageRow, ...],
    start_index: int | None,
    end_index: int | None,
) -> tuple[LightroomChosenImageRow, ...]:
    if start_index is None and end_index is None:
        return image_rows

    normalized_start = 1 if start_index is None else start_index
    normalized_end = len(image_rows) if end_index is None else end_index
    if normalized_start > normalized_end:
        raise ValueError(
            "Lightroom asset range start index must be less than or equal to the end index."
        )

    start_offset = max(normalized_start - 1, 0)
    end_offset = max(normalized_end, 0)
    return image_rows[start_offset:end_offset]


__all__ = ["LightroomCatalogTransformer"]
