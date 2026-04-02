"""Pure transformation tests for Lightroom catalog asset candidate mapping."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from pixelpast.ingestion.lightroom_catalog import (
    LightroomCatalogDescriptor,
    LightroomCatalogFetcher,
    LightroomCatalogTransformer,
    LightroomChosenImageRow,
    LightroomCollectionRow,
    LightroomFaceRow,
    LightroomKeywordRow,
)

_FIXTURE_PATH = Path("test/assets/lightroom-classic-catalog-test-fixture.lrcat")


def test_lightroom_transformer_maps_fixture_row_to_asset_candidate() -> None:
    loaded_catalog = LightroomCatalogFetcher().fetch_catalogs(
        catalogs=(LightroomCatalogDescriptor(path=_FIXTURE_PATH),)
    )[0]

    candidate = LightroomCatalogTransformer().build_catalog_candidate(
        loaded_catalog
    ).assets[1]

    assert candidate.external_id == "4E7C6031A061CE51AF186FE5022D4BFB"
    assert candidate.media_type == "photo"
    assert candidate.timestamp == datetime(2020, 1, 1, 2, 3, 40, tzinfo=UTC)
    assert candidate.summary == "Title 2"
    assert candidate.latitude == pytest.approx(48.86039605)
    assert candidate.longitude == pytest.approx(2.334584866666667)
    assert candidate.creator_name == "Leonardo da Vinci"
    assert candidate.tag_paths == (
        "events",
        "events|vacation",
        "events|vacation|Italy",
        "events|vacation|Italy|San Marino",
    )
    assert candidate.asset_tag_paths == (
        "events|vacation|Italy",
        "events|vacation|Italy|San Marino",
        "events",
        "events|vacation",
    )
    assert tuple((person.name, person.path) for person in candidate.persons) == (
        ("John Doe", "who|Persons|John Doe"),
        ("Mona Lisa", "who|Persons|Mona Lisa"),
    )
    assert candidate.folder_path == (
        "C:/Users/phili/Desktop/Source/pixelpast-core/test/assets"
    )
    assert candidate.collections == ()
    assert candidate.metadata_json == {
        "file_name": "monalisa-2.jpg",
        "file_path": (
            "C:/Users/phili/Desktop/Source/pixelpast-core/test/assets/"
            "monalisa-2.jpg"
        ),
        "preserved_file_name": "monalisa-2.jpg",
        "caption": None,
        "camera": None,
        "lens": None,
        "aperture_f_number": None,
        "shutter_speed_seconds": None,
        "iso": None,
        "rating": 4,
        "color_label": "Gelb",
        "explicit_keywords": [
            "Italy",
            "John Doe",
            "Mona Lisa",
            "San Marino",
            "events",
            "vacation",
        ],
        "hierarchical_subjects": [
            "events|vacation",
            "events|vacation|Italy|San Marino",
            "who|Persons|John Doe",
            "who|Persons|Mona Lisa",
        ],
        "linked_tag_paths": [
            "events|vacation|Italy",
            "events|vacation|Italy|San Marino",
            "events",
            "events|vacation",
        ],
        "collections": [],
        "face_regions": [
            {
                "name": "Mona Lisa",
                "left": 0.10048499999999999,
                "top": 0.09559,
                "right": 0.348035,
                "bottom": 0.33701,
            },
            {
                "name": "John Doe",
                "left": 0.486525,
                "top": 0.460785,
                "right": 0.814955,
                "bottom": 0.8063750000000001,
            },
        ],
    }


def test_lightroom_transformer_converts_apex_values_and_normalizes_person_links() -> (
    None
):
    transformer = LightroomCatalogTransformer()

    candidate = transformer.build_asset_candidate(
        image_row=LightroomChosenImageRow(
            image_id=1,
            root_file_id=1,
            file_name="example.cr3",
            file_path="C:/photos/example.cr3",
            capture_time_text="2020-01-01T02:03:40+02:00",
            rating=5,
            color_label=" Red ",
            xmp_blob=_FIXTURE_ROW.xmp_blob,
            caption=" Caption ",
            creator_name=" Creator ",
            camera=" Canon EOS R5 ",
            lens=" RF24-70mm ",
            aperture_apex=4.6438561898,
            shutter_speed_apex=7.6438561898,
            iso_speed_rating=400.0,
            gps_latitude=10.5,
            gps_longitude=20.5,
        ),
        face_rows=(
            LightroomFaceRow(
                image_id=1,
                face_id=2,
                name="Mona Lisa",
                left=0.2,
                top=0.1,
                right=0.4,
                bottom=0.3,
                region_type=1.0,
                orientation=0.0,
            ),
            LightroomFaceRow(
                image_id=1,
                face_id=3,
                name="Mona Lisa",
                left=0.5,
                top=0.4,
                right=0.7,
                bottom=0.6,
                region_type=1.0,
                orientation=0.0,
            ),
        ),
        keyword_rows=(
            LightroomKeywordRow(
                image_id=1,
                keyword_id=97,
                keyword_name="Mona Lisa",
                keyword_path="who|Persons|Mona Lisa",
                keyword_type="person",
            ),
        ),
        collection_rows=(
            LightroomCollectionRow(
                image_id=1,
                collection_id=9,
                collection_name="Favorites",
                collection_path="Root/Favorites",
                parent_collection_id=None,
                collection_type="lightroom_collection",
            ),
        ),
    )

    assert candidate.timestamp == datetime(2020, 1, 1, 0, 3, 40, tzinfo=UTC)
    assert candidate.tag_paths == (
        "events",
        "events|vacation",
        "events|vacation|München",
    )
    assert candidate.asset_tag_paths == (
        "events|vacation|München",
        "events",
        "events|vacation",
    )
    assert tuple((person.name, person.path) for person in candidate.persons) == (
        ("Mona Lisa", "who|Persons|Mona Lisa"),
    )
    assert candidate.metadata_json is not None
    assert candidate.metadata_json["caption"] == "Caption"
    assert candidate.metadata_json["camera"] == "Canon EOS R5"
    assert candidate.metadata_json["lens"] == "RF24-70mm"
    assert candidate.metadata_json["aperture_f_number"] == pytest.approx(5.0)
    assert candidate.metadata_json["shutter_speed_seconds"] == pytest.approx(0.005)
    assert candidate.metadata_json["iso"] == 400
    assert candidate.metadata_json["color_label"] == "Red"
    assert candidate.metadata_json["explicit_keywords"] == [
        "Mona Lisa",
        "München",
        "events",
        "vacation",
    ]
    assert candidate.metadata_json["hierarchical_subjects"] == [
        "events",
        "events|vacation|München",
        "who|Persons|Mona Lisa",
    ]
    assert candidate.metadata_json["linked_tag_paths"] == [
        "events|vacation|München",
        "events",
        "events|vacation",
    ]
    assert candidate.folder_path == "C:/photos"
    assert tuple(
        (
            membership.collection_id,
            membership.name,
            membership.path,
            membership.collection_type,
        )
        for membership in candidate.collections
    ) == (
        (9, "Favorites", "Root/Favorites", "lightroom_collection"),
    )
    assert candidate.metadata_json["collections"] == [
        {"id": 9, "name": "Favorites", "path": "Root/Favorites"}
    ]
    assert candidate.metadata_json["face_regions"] == [
        {
            "name": "Mona Lisa",
            "left": 0.2,
            "top": 0.1,
            "right": 0.4,
            "bottom": 0.3,
        },
        {
            "name": "Mona Lisa",
            "left": 0.5,
            "top": 0.4,
            "right": 0.7,
            "bottom": 0.6,
        },
    ]


def test_lightroom_transformer_creates_people_from_person_keyword_type_without_face_regions() -> None:
    transformer = LightroomCatalogTransformer()

    candidate = transformer.build_asset_candidate(
        image_row=LightroomChosenImageRow(
            image_id=1,
            root_file_id=1,
            file_name="example.jpg",
            file_path="C:/photos/example.jpg",
            capture_time_text="2020-01-01T02:03:40.000",
            rating=None,
            color_label=None,
            xmp_blob=_FIXTURE_ROW.xmp_blob,
            caption=None,
            creator_name=None,
            camera=None,
            lens=None,
            aperture_apex=None,
            shutter_speed_apex=None,
            iso_speed_rating=None,
            gps_latitude=None,
            gps_longitude=None,
        ),
        face_rows=(),
        keyword_rows=(
            LightroomKeywordRow(
                image_id=1,
                keyword_id=97,
                keyword_name="Mona Lisa",
                keyword_path="who|Persons|Mona Lisa",
                keyword_type="person",
            ),
        ),
        collection_rows=(),
    )

    assert tuple((person.name, person.path) for person in candidate.persons) == (
        ("Mona Lisa", "who|Persons|Mona Lisa"),
    )
    assert all("who|" not in path for path in candidate.tag_paths)


_FIXTURE_ROW = LightroomCatalogFetcher().fetch_catalogs(
    catalogs=(LightroomCatalogDescriptor(path=_FIXTURE_PATH),)
)[0].chosen_images[0]
