"""Characterization tests for Lightroom catalog ingestion contracts and fixture."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree

from pixelpast.ingestion.lightroom_catalog import (
    LightroomAssetCandidate,
    LightroomCatalogCandidate,
    LightroomCatalogDescriptor,
    LightroomCatalogTransformer,
    LightroomChosenImageRow,
    LightroomCollectionMembership,
    LightroomCollectionNode,
    LightroomFaceRegion,
    LightroomIngestionResult,
    LightroomPersonCandidate,
    LightroomTransformError,
    LightroomXmpPayload,
    decompress_lightroom_xmp_blob,
    parse_lightroom_xmp_payload,
)
from pixelpast.ingestion.lightroom_catalog import contracts as lightroom_contracts
from pixelpast.ingestion.lightroom_catalog import xmp as lightroom_xmp
from pixelpast.persistence.models import Asset

_FIXTURE_PATH = Path("test/assets/lightroom-classic-catalog-test-fixture.lrcat")
_RDF_TAG = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF"
_DESCRIPTION_TAG = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description"


def test_lightroom_catalog_public_contract_imports_remain_stable() -> None:
    assert LightroomCatalogDescriptor is lightroom_contracts.LightroomCatalogDescriptor
    assert LightroomChosenImageRow is lightroom_contracts.LightroomChosenImageRow
    assert LightroomXmpPayload is lightroom_contracts.LightroomXmpPayload
    assert LightroomPersonCandidate is lightroom_contracts.LightroomPersonCandidate
    assert LightroomFaceRegion is lightroom_contracts.LightroomFaceRegion
    assert (
        LightroomCollectionMembership
        is lightroom_contracts.LightroomCollectionMembership
    )
    assert LightroomCollectionNode is lightroom_contracts.LightroomCollectionNode
    assert LightroomAssetCandidate is lightroom_contracts.LightroomAssetCandidate
    assert LightroomCatalogCandidate is lightroom_contracts.LightroomCatalogCandidate
    assert LightroomTransformError is lightroom_contracts.LightroomTransformError
    assert LightroomIngestionResult is lightroom_contracts.LightroomIngestionResult
    assert LightroomCatalogTransformer.__name__ == "LightroomCatalogTransformer"
    assert (
        decompress_lightroom_xmp_blob
        is lightroom_xmp.decompress_lightroom_xmp_blob
    )
    assert parse_lightroom_xmp_payload is lightroom_xmp.parse_lightroom_xmp_payload


def test_lightroom_fixture_catalog_is_sqlite_and_exposes_connector_tables() -> None:
    descriptor = LightroomCatalogDescriptor(path=_FIXTURE_PATH)

    with sqlite3.connect(descriptor.origin_path) as connection:
        cursor = connection.cursor()
        cursor.execute("PRAGMA schema_version")
        schema_version = cursor.fetchone()[0]
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        table_names = {row[0] for row in cursor.fetchall()}

    assert descriptor.origin_label == _FIXTURE_PATH.resolve().as_posix()
    assert schema_version > 0
    assert {
        "Adobe_AdditionalMetadata",
        "Adobe_images",
        "AgHarvestedExifMetadata",
        "AgHarvestedIptcMetadata",
        "AgInternedIptcCreator",
        "AgLibraryCollection",
        "AgLibraryCollectionImage",
        "AgLibraryFace",
        "AgLibraryFile",
        "AgLibraryFolder",
        "AgLibraryIPTC",
        "AgLibraryKeyword",
        "AgLibraryKeywordFace",
        "AgLibraryKeywordImage",
        "AgLibraryRootFolder",
    }.issubset(table_names)


def test_lightroom_fixture_characterizes_chosen_images_and_join_boundaries() -> None:
    rows = _fetch_chosen_image_rows()

    assert rows == (
        LightroomChosenImageRow(
            image_id=67,
            root_file_id=71,
            file_name="monalisa-1.jpg",
            file_path=(
                "C:/Users/phili/Desktop/Source/pixelpast-core/test/assets/"
                "monalisa-1.jpg"
            ),
            capture_time_text="2020-01-01T02:03:40.000",
            rating=3,
            color_label="Rot",
            xmp_blob=rows[0].xmp_blob,
            caption=None,
            creator_name="Leonardo da Vinci",
            camera=None,
            lens=None,
            aperture_apex=None,
            shutter_speed_apex=None,
            iso_speed_rating=None,
            gps_latitude=48.86189241666667,
            gps_longitude=2.3358866333333332,
        ),
        LightroomChosenImageRow(
            image_id=68,
            root_file_id=118,
            file_name="monalisa-2.jpg",
            file_path=(
                "C:/Users/phili/Desktop/Source/pixelpast-core/test/assets/"
                "monalisa-2.jpg"
            ),
            capture_time_text="2020-01-01T02:03:40.000",
            rating=4,
            color_label="Gelb",
            xmp_blob=rows[1].xmp_blob,
            caption=None,
            creator_name="Leonardo da Vinci",
            camera=None,
            lens=None,
            aperture_apex=None,
            shutter_speed_apex=None,
            iso_speed_rating=None,
            gps_latitude=48.86039605,
            gps_longitude=2.334584866666667,
        ),
        LightroomChosenImageRow(
            image_id=69,
            root_file_id=174,
            file_name="monalisa-3.jpg",
            file_path=(
                "C:/Users/phili/Desktop/Source/pixelpast-core/test/assets/"
                "monalisa-3.jpg"
            ),
            capture_time_text="2020-01-01T02:03:40.000",
            rating=5,
            color_label="Gr\u00fcn",
            xmp_blob=rows[2].xmp_blob,
            caption=None,
            creator_name="Leonardo da Vinci",
            camera=None,
            lens=None,
            aperture_apex=None,
            shutter_speed_apex=None,
            iso_speed_rating=None,
            gps_latitude=48.860383066666664,
            gps_longitude=2.3385617666666665,
        ),
    )

    with sqlite3.connect(_FIXTURE_PATH) as connection:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT image FROM Adobe_AdditionalMetadata ORDER BY image"
        )
        additional_metadata_image_ids = tuple(row[0] for row in cursor.fetchall())
        cursor.execute("SELECT image FROM AgHarvestedExifMetadata ORDER BY image")
        exif_image_ids = tuple(row[0] for row in cursor.fetchall())
        cursor.execute("SELECT image FROM AgHarvestedIptcMetadata ORDER BY image")
        creator_image_ids = tuple(row[0] for row in cursor.fetchall())
        cursor.execute("SELECT image FROM AgLibraryIPTC ORDER BY image")
        iptc_image_ids = tuple(row[0] for row in cursor.fetchall())

    assert additional_metadata_image_ids == (67, 68, 69)
    assert exif_image_ids == (67, 68, 69)
    assert creator_image_ids == (67, 68, 69)
    assert iptc_image_ids == (67, 68, 69)


def test_lightroom_fixture_pins_xmp_blob_decompression_rule_and_xml_shape() -> None:
    first_row = _fetch_chosen_image_rows()[0]

    xml_bytes = decompress_lightroom_xmp_blob(first_row.xmp_blob)
    root = ElementTree.fromstring(xml_bytes)
    payload = parse_lightroom_xmp_payload(
        image_id=first_row.image_id,
        blob=first_row.xmp_blob,
    )

    assert isinstance(first_row.xmp_blob, bytes)
    assert len(first_row.xmp_blob[:4]) == 4
    assert root.tag == "{adobe:ns:meta/}xmpmeta"
    assert root.find(_RDF_TAG) is not None
    assert root.find(f"{_RDF_TAG}/{_DESCRIPTION_TAG}") is not None
    assert payload == LightroomXmpPayload(
        image_id=67,
        xml_text=xml_bytes.decode("utf-8"),
        document_id="3EC1FA8A05CE57D59B0BA4C353580C5F",
        preserved_file_name="monalisa-1.jpg",
        title="Title 1",
        explicit_keywords=("Mona Lisa", "München", "events", "vacation"),
        hierarchical_keywords=(
            "events",
            "events|vacation|M\u00fcnchen",
            "who|Persons|Mona Lisa",
        ),
    )


def test_lightroom_fixture_contains_xmp_titles_keywords_faces_and_creator_metadata() -> (
    None
):
    chosen_rows = _fetch_chosen_image_rows()
    xmp_payloads = tuple(
        parse_lightroom_xmp_payload(image_id=row.image_id, blob=row.xmp_blob)
        for row in chosen_rows
    )
    face_names_by_image = _fetch_face_names_by_image()

    assert [payload.document_id for payload in xmp_payloads] == [
        "3EC1FA8A05CE57D59B0BA4C353580C5F",
        "4E7C6031A061CE51AF186FE5022D4BFB",
        "0B2B664356B0F811D277461F8953ABE4",
    ]
    assert [payload.preserved_file_name for payload in xmp_payloads] == [
        "monalisa-1.jpg",
        "monalisa-2.jpg",
        "monalisa-3.jpg",
    ]
    assert [payload.title for payload in xmp_payloads] == [
        "Title 1",
        "Title 2",
        "Title 3 \u00e4\u00f6\u00fc\u00df\u00c4\u00d6\u00dc",
    ]
    assert xmp_payloads[0].explicit_keywords == (
        "Mona Lisa",
        "München",
        "events",
        "vacation",
    )
    assert xmp_payloads[1].explicit_keywords == (
        "Italy",
        "John Doe",
        "Mona Lisa",
        "San Marino",
        "events",
        "vacation",
    )
    assert xmp_payloads[2].explicit_keywords == (
        "John Doe",
        "Mona Lisa",
        "München",
        "events",
        "vacation",
        "wedding",
    )
    assert xmp_payloads[1].hierarchical_keywords == (
        "events|vacation",
        "events|vacation|Italy|San Marino",
        "who|Persons|John Doe",
        "who|Persons|Mona Lisa",
    )
    assert xmp_payloads[2].hierarchical_keywords == (
        "events|vacation|M\u00fcnchen",
        "events|wedding",
        "who|Persons|John Doe",
        "who|Persons|Mona Lisa",
    )
    assert [row.creator_name for row in chosen_rows] == [
        "Leonardo da Vinci",
        "Leonardo da Vinci",
        "Leonardo da Vinci",
    ]
    assert [row.caption for row in chosen_rows] == [None, None, None]
    assert face_names_by_image == {
        67: ("Mona Lisa",),
        68: ("John Doe", "Mona Lisa"),
        69: ("John Doe", "John Doe", "Mona Lisa"),
    }


def test_lightroom_fixture_currently_has_no_static_collection_memberships() -> None:
    with sqlite3.connect(_FIXTURE_PATH) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM AgLibraryCollectionImage")
        static_membership_count = cursor.fetchone()[0]
        cursor.execute(
            "SELECT name FROM AgLibraryCollection "
            "WHERE creationId = 'com.adobe.ag.library.smart_collection' "
            "ORDER BY name"
        )
        smart_collection_names = tuple(row[0] for row in cursor.fetchall())

    assert static_membership_count == 0
    assert smart_collection_names == (
        "F\u00fcnf Sterne",
        "K\u00fcrzlich ge\u00e4ndert",
        "Past Month",
        "Rot gef\u00e4rbt",
        "Videodateien",
        "Without Keywords",
    )


def test_lightroom_contracts_pin_existing_asset_storage_boundary_without_schema_changes() -> (
    None
):
    candidate = LightroomAssetCandidate(
        external_id="3EC1FA8A05CE57D59B0BA4C353580C5F",
        media_type="photo",
        timestamp=datetime(2020, 1, 1, 2, 3, 40, tzinfo=UTC),
        summary="Title 1",
        latitude=48.86189241666667,
        longitude=2.3358866333333332,
        creator_name="Leonardo da Vinci",
        tag_paths=(
            "events",
            "events|vacation",
            "events|vacation|M\u00fcnchen",
            "who",
            "who|Persons",
            "who|Persons|Mona Lisa",
        ),
        asset_tag_paths=("events", "events|vacation", "events|vacation|M\u00fcnchen"),
        persons=(
            LightroomPersonCandidate(
                name="Mona Lisa",
                path="who|Persons|Mona Lisa",
            ),
        ),
        folder_path="C:/Users/phili/Desktop/Source/pixelpast-core/test/assets",
        collections=(),
        metadata_json={
            "file_name": "monalisa-1.jpg",
            "file_path": (
                "C:/Users/phili/Desktop/Source/pixelpast-core/test/assets/"
                "monalisa-1.jpg"
            ),
            "preserved_file_name": "monalisa-1.jpg",
            "caption": None,
            "camera": None,
            "lens": None,
            "aperture_f_number": None,
            "shutter_speed_seconds": None,
            "iso": None,
            "rating": 3,
            "color_label": "Rot",
            "explicit_keywords": ["Mona Lisa", "München", "events", "vacation"],
            "hierarchical_subjects": [
                "events",
                "events|vacation|München",
                "who|Persons|Mona Lisa",
            ],
            "linked_tag_paths": [
                "events|vacation|München",
                "events",
                "events|vacation",
            ],
            "collections": [],
            "face_regions": [
                {
                    "name": "Mona Lisa",
                    "left": 0.29167,
                    "top": 0.25980499999999995,
                    "right": 0.58579,
                    "bottom": 0.537995,
                }
            ],
        },
    )
    catalog_candidate = LightroomCatalogCandidate(
        catalog=LightroomCatalogDescriptor(path=_FIXTURE_PATH),
        chosen_images=_fetch_chosen_image_rows(),
        collections=(),
        assets=(candidate,),
    )

    assert catalog_candidate.catalog.origin_label == _FIXTURE_PATH.resolve().as_posix()
    assert len(catalog_candidate.assets) == 1
    assert len(catalog_candidate.chosen_images) == 3
    assert hasattr(Asset, "metadata_json")
    assert not hasattr(Asset, "raw_payload")
    assert not hasattr(Asset, "file_path")
    assert not hasattr(Asset, "caption")


def _fetch_chosen_image_rows() -> tuple[LightroomChosenImageRow, ...]:
    with sqlite3.connect(_FIXTURE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        cursor.execute(
            """
            WITH chosen_images AS (
                SELECT rootFile, MIN(id_local) AS image_id
                FROM Adobe_images
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
            """
        )
        rows = cursor.fetchall()

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


def _fetch_face_names_by_image() -> dict[int, tuple[str, ...]]:
    with sqlite3.connect(_FIXTURE_PATH) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT face.image, keyword.name
            FROM AgLibraryFace face
            JOIN AgLibraryKeywordFace keyword_face ON keyword_face.face = face.id_local
            JOIN AgLibraryKeyword keyword ON keyword.id_local = keyword_face.tag
            ORDER BY face.image, keyword.name
            """
        )
        rows = cursor.fetchall()

    face_names_by_image: dict[int, list[str]] = {}
    for image_id, name in rows:
        face_names_by_image.setdefault(image_id, []).append(name)
    return {
        image_id: tuple(names)
        for image_id, names in face_names_by_image.items()
    }


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
