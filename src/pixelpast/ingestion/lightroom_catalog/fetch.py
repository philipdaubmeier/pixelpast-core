"""Read-only SQLite loading for Lightroom Classic catalog ingestion."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from pixelpast.ingestion.lightroom_catalog.contracts import (
    LoadedLightroomCatalog,
    LightroomCatalogDescriptor,
    LightroomChosenImageRow,
    LightroomCollectionRow,
    LightroomFaceRow,
)


@dataclass(slots=True, frozen=True)
class LightroomCatalogLoadProgress:
    """Represents one raw Lightroom catalog load transition."""

    event: str
    catalog: LightroomCatalogDescriptor
    catalog_index: int
    catalog_total: int


class LightroomCatalogFetcher:
    """Load bounded Lightroom catalog rows from a read-only SQLite connection."""

    def fetch_catalogs(
        self,
        *,
        catalogs: Sequence[LightroomCatalogDescriptor],
        start_index: int | None = None,
        end_index: int | None = None,
        on_catalog_progress: (
            Callable[[LightroomCatalogLoadProgress], None] | None
        ) = None,
    ) -> tuple[LoadedLightroomCatalog, ...]:
        """Return read-only loaded catalog payloads in deterministic input order."""

        loaded_catalogs: list[LoadedLightroomCatalog] = []
        catalog_total = len(catalogs)
        for index, catalog in enumerate(catalogs, start=1):
            if on_catalog_progress is not None:
                on_catalog_progress(
                    LightroomCatalogLoadProgress(
                        event="submitted",
                        catalog=catalog,
                        catalog_index=index,
                        catalog_total=catalog_total,
                    )
                )
            loaded_catalogs.append(
                self._fetch_catalog(
                    catalog=catalog,
                    start_index=start_index,
                    end_index=end_index,
                )
            )
            if on_catalog_progress is not None:
                on_catalog_progress(
                    LightroomCatalogLoadProgress(
                        event="completed",
                        catalog=catalog,
                        catalog_index=index,
                        catalog_total=catalog_total,
                    )
                )
        return tuple(loaded_catalogs)

    def _fetch_catalog(
        self,
        *,
        catalog: LightroomCatalogDescriptor,
        start_index: int | None = None,
        end_index: int | None = None,
    ) -> LoadedLightroomCatalog:
        with open_lightroom_catalog_read_only(catalog.origin_path) as connection:
            chosen_images = _fetch_chosen_image_rows(
                connection,
                start_index=start_index,
                end_index=end_index,
            )
            image_ids = tuple(row.image_id for row in chosen_images)
            face_rows = _fetch_face_rows(connection, image_ids=image_ids)
            collection_rows = _fetch_collection_rows(connection, image_ids=image_ids)
        return LoadedLightroomCatalog(
            descriptor=catalog,
            chosen_images=chosen_images,
            face_rows=face_rows,
            collection_rows=collection_rows,
        )


def open_lightroom_catalog_read_only(path: Path) -> sqlite3.Connection:
    """Open one Lightroom catalog through SQLite's read-only URI mode."""

    connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _fetch_chosen_image_rows(
    connection: sqlite3.Connection,
    *,
    start_index: int | None = None,
    end_index: int | None = None,
) -> tuple[LightroomChosenImageRow, ...]:
    limit_clause, limit_parameters = _build_limit_clause(
        start_index=start_index,
        end_index=end_index,
    )
    rows = connection.execute(
        f"""
        WITH chosen_images AS (
            SELECT rootFile, MIN(id_local) AS image_id
            FROM Adobe_images
            WHERE rootFile IS NOT NULL
            GROUP BY rootFile
        )
        SELECT
            ai.id_local AS image_id,
            ai.rootFile AS root_file_id,
            file.baseName AS file_base_name,
            file.extension AS file_extension,
            root_folder.absolutePath AS root_absolute_path,
            folder.pathFromRoot AS folder_path_from_root,
            ai.captureTime AS capture_time_text,
            ai.rating AS rating,
            ai.colorLabels AS color_label,
            metadata.xmp AS xmp_blob,
            iptc.caption AS caption,
            creator.value AS creator_name,
            camera.value AS camera,
            lens.value AS lens,
            exif.aperture AS aperture_apex,
            exif.shutterSpeed AS shutter_speed_apex,
            exif.isoSpeedRating AS iso_speed_rating,
            exif.gpsLatitude AS gps_latitude,
            exif.gpsLongitude AS gps_longitude
        FROM chosen_images chosen
        JOIN Adobe_images ai ON ai.id_local = chosen.image_id
        JOIN AgLibraryFile file ON file.id_local = ai.rootFile
        JOIN AgLibraryFolder folder ON folder.id_local = file.folder
        JOIN AgLibraryRootFolder root_folder
            ON root_folder.id_local = folder.rootFolder
        JOIN Adobe_AdditionalMetadata metadata ON metadata.image = ai.id_local
        LEFT JOIN AgLibraryIPTC iptc ON iptc.image = ai.id_local
        LEFT JOIN AgHarvestedExifMetadata exif ON exif.image = ai.id_local
        LEFT JOIN AgInternedExifCameraModel camera
            ON camera.id_local = exif.cameraModelRef
        LEFT JOIN AgInternedExifLens lens
            ON lens.id_local = exif.lensRef
        LEFT JOIN AgHarvestedIptcMetadata harvested ON harvested.image = ai.id_local
        LEFT JOIN AgInternedIptcCreator creator
            ON creator.id_local = harvested.creatorRef
        ORDER BY ai.id_local
        {limit_clause}
        """,
        limit_parameters,
    ).fetchall()

    return tuple(
        LightroomChosenImageRow(
            image_id=row["image_id"],
            root_file_id=row["root_file_id"],
            file_name=_build_file_name(
                base_name=row["file_base_name"],
                extension=row["file_extension"],
            ),
            file_path=_build_file_path(
                root_absolute_path=row["root_absolute_path"],
                folder_path_from_root=row["folder_path_from_root"],
                file_name=_build_file_name(
                    base_name=row["file_base_name"],
                    extension=row["file_extension"],
                ),
            ),
            capture_time_text=row["capture_time_text"],
            rating=_coerce_optional_int(row["rating"]),
            color_label=row["color_label"],
            xmp_blob=row["xmp_blob"],
            caption=row["caption"],
            creator_name=row["creator_name"],
            camera=row["camera"],
            lens=row["lens"],
            aperture_apex=row["aperture_apex"],
            shutter_speed_apex=row["shutter_speed_apex"],
            iso_speed_rating=row["iso_speed_rating"],
            gps_latitude=row["gps_latitude"],
            gps_longitude=row["gps_longitude"],
        )
        for row in rows
    )


def _fetch_face_rows(
    connection: sqlite3.Connection,
    *,
    image_ids: tuple[int, ...],
) -> tuple[LightroomFaceRow, ...]:
    if not image_ids:
        return ()

    rows: list[sqlite3.Row] = []
    for batch_image_ids in _iter_sql_batches(image_ids):
        rows.extend(
            connection.execute(
                f"""
                SELECT
                    face.image AS image_id,
                    face.id_local AS face_id,
                    keyword.name AS name,
                    face.tl_x AS left,
                    face.tl_y AS top,
                    face.tr_x AS right,
                    face.bl_y AS bottom,
                    face.regionType AS region_type,
                    face.orientation AS orientation
                FROM AgLibraryFace face
                LEFT JOIN AgLibraryKeywordFace keyword_face
                    ON keyword_face.face = face.id_local
                LEFT JOIN AgLibraryKeyword keyword
                    ON keyword.id_local = keyword_face.tag
                WHERE face.image IN ({_sql_placeholders(len(batch_image_ids))})
                ORDER BY face.image, face.id_local, keyword.name
                """,
                batch_image_ids,
            ).fetchall()
        )

    return tuple(
        LightroomFaceRow(
            image_id=row["image_id"],
            face_id=row["face_id"],
            name=row["name"],
            left=row["left"],
            top=row["top"],
            right=row["right"],
            bottom=row["bottom"],
            region_type=row["region_type"],
            orientation=row["orientation"],
        )
        for row in rows
    )


def _fetch_collection_rows(
    connection: sqlite3.Connection,
    *,
    image_ids: tuple[int, ...],
) -> tuple[LightroomCollectionRow, ...]:
    if not image_ids:
        return ()

    membership_rows: list[sqlite3.Row] = []
    for batch_image_ids in _iter_sql_batches(image_ids):
        membership_rows.extend(
            connection.execute(
                f"""
                SELECT
                    membership.image AS image_id,
                    collection.id_local AS collection_id,
                    collection.name AS collection_name,
                    collection.parent AS parent_collection_id
                FROM AgLibraryCollectionImage membership
                JOIN AgLibraryCollection collection
                    ON collection.id_local = membership.collection
                WHERE membership.image IN ({_sql_placeholders(len(batch_image_ids))})
                ORDER BY membership.image, collection.id_local
                """,
                batch_image_ids,
            ).fetchall()
        )
    if not membership_rows:
        return ()

    collection_lookup = _load_collection_lookup(
        connection,
        collection_ids={
            int(row["collection_id"]) for row in membership_rows if row["collection_id"]
        },
    )
    return tuple(
        LightroomCollectionRow(
            image_id=row["image_id"],
            collection_id=row["collection_id"],
            collection_name=row["collection_name"],
            collection_path=_build_collection_path(
                collection_id=row["collection_id"],
                collection_lookup=collection_lookup,
            ),
            parent_collection_id=_coerce_optional_int(row["parent_collection_id"]),
        )
        for row in membership_rows
    )


def _load_collection_lookup(
    connection: sqlite3.Connection,
    *,
    collection_ids: set[int],
) -> dict[int, tuple[str, int | None]]:
    collection_lookup: dict[int, tuple[str, int | None]] = {}
    pending_collection_ids = set(collection_ids)
    while pending_collection_ids:
        rows = connection.execute(
            f"""
            SELECT id_local, name, parent
            FROM AgLibraryCollection
            WHERE id_local IN ({_sql_placeholders(len(pending_collection_ids))})
            """,
            tuple(sorted(pending_collection_ids)),
        ).fetchall()
        pending_collection_ids = set()
        for row in rows:
            collection_id = int(row["id_local"])
            parent_collection_id = _coerce_optional_int(row["parent"])
            collection_lookup[collection_id] = (row["name"], parent_collection_id)
            if (
                parent_collection_id is not None
                and parent_collection_id not in collection_lookup
            ):
                pending_collection_ids.add(parent_collection_id)
    return collection_lookup


def _build_collection_path(
    *,
    collection_id: int,
    collection_lookup: dict[int, tuple[str, int | None]],
) -> str:
    path_segments: list[str] = []
    current_collection_id: int | None = collection_id
    while current_collection_id is not None:
        name, current_collection_id = collection_lookup[current_collection_id]
        path_segments.append(name)
    path_segments.reverse()
    return "/".join(path_segments)


def _build_file_name(*, base_name: str, extension: str | None) -> str:
    if extension:
        return f"{base_name}.{extension}"
    return base_name


def _build_file_path(
    *,
    root_absolute_path: str,
    folder_path_from_root: str,
    file_name: str,
) -> str:
    return (
        Path(root_absolute_path.replace("\\", "/"))
        / folder_path_from_root.replace("\\", "/")
        / file_name
    ).as_posix()


def _coerce_optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _sql_placeholders(count: int) -> str:
    return ", ".join("?" for _ in range(count))


def _build_limit_clause(
    *,
    start_index: int | None,
    end_index: int | None,
) -> tuple[str, tuple[int, ...]]:
    if start_index is None and end_index is None:
        return "", ()

    normalized_start = 1 if start_index is None else start_index
    normalized_end = end_index
    offset = normalized_start - 1
    if normalized_end is None:
        return "LIMIT -1 OFFSET ?", (offset,)

    limit = normalized_end - normalized_start + 1
    return "LIMIT ? OFFSET ?", (limit, offset)


def _iter_sql_batches(
    values: Iterable[int],
    *,
    batch_size: int = 900,
) -> Iterable[tuple[int, ...]]:
    batch: list[int] = []
    for value in values:
        batch.append(value)
        if len(batch) == batch_size:
            yield tuple(batch)
            batch = []
    if batch:
        yield tuple(batch)


__all__ = [
    "LightroomCatalogFetcher",
    "LightroomCatalogLoadProgress",
    "open_lightroom_catalog_read_only",
]
