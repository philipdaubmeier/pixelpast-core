"""Unit tests for pure photo metadata transformation logic."""

from __future__ import annotations

import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pixelpast.ingestion.photos import PhotoPersonCandidate
from pixelpast.ingestion.photos.transform import (
    PhotoExifMetadata,
    PhotoMetadataTransformer,
)


def test_photo_metadata_transformer_builds_canonical_candidate_from_metadata() -> None:
    workspace_root = _create_workspace_dir(prefix="photo-transform-canonical")
    try:
        photo_path = workspace_root / "image.jpg"
        photo_path.write_bytes(b"photo")

        candidate = PhotoMetadataTransformer().build_asset_candidate(
            path=photo_path.resolve(),
            metadata={
                "XMP-dc:Title": "XMP Title",
                "XMP-dc:Creator": "XMP Creator",
                "ExifIFD:DateTimeOriginal": "2020:01:01 02:03:40",
                "Composite:GPSLatitude": 48.86,
                "Composite:GPSLongitude": 2.33,
                "XMP-dc:Subject": ["events", "Mona Lisa", "vacation", "events"],
                "XMP-lr:HierarchicalSubject": [
                    "who|Persons|Mona Lisa",
                    "events|vacation|Italy",
                ],
                "XMP-mwg-rs:RegionName": ["Mona Lisa", "Not a Face"],
                "XMP-mwg-rs:RegionType": ["Face", "Pet"],
            },
            fallback_exif=PhotoExifMetadata(
                timestamp=datetime(2024, 1, 2, 3, 4, 5, tzinfo=UTC),
                latitude=1.0,
                longitude=2.0,
            ),
        )

        assert candidate.external_id == photo_path.resolve().as_posix()
        assert candidate.summary == "XMP Title"
        assert candidate.creator_name == "XMP Creator"
        assert candidate.timestamp == datetime(2020, 1, 1, 2, 3, 40, tzinfo=UTC)
        assert candidate.latitude == 48.86
        assert candidate.longitude == 2.33
        assert candidate.tag_paths == (
            "events",
            "events|vacation",
            "events|vacation|Italy",
        )
        assert candidate.asset_tag_paths == ("events", "events|vacation")
        assert candidate.persons == (
            PhotoPersonCandidate(name="Mona Lisa", path="who|Persons|Mona Lisa"),
        )
        assert candidate.metadata_json == {
            "source_path": photo_path.resolve().as_posix(),
            "resolution": {
                "title": "XMP-dc:Title",
                "timestamp": "ExifIFD:DateTimeOriginal",
                "gps": "Composite:GPSLatitude,Composite:GPSLongitude",
                "creator": "XMP-dc:Creator",
            },
            "title": "XMP Title",
            "creator_name": "XMP Creator",
            "explicit_keywords": ["events", "Mona Lisa", "vacation"],
            "hierarchical_subjects": [
                "who|Persons|Mona Lisa",
                "events|vacation|Italy",
            ],
            "linked_tag_paths": ["events", "events|vacation"],
            "persons": [
                {
                    "name": "Mona Lisa",
                    "path": "who|Persons|Mona Lisa",
                }
            ],
        }
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_photo_metadata_transformer_applies_fallback_timestamp_and_gps_sources(
) -> None:
    workspace_root = _create_workspace_dir(prefix="photo-transform-fallback")
    try:
        filename_photo = workspace_root / "IMG_20230304_050607.jpg"
        filename_photo.write_bytes(b"photo")
        os.utime(filename_photo, (1_720_000_000, 1_720_000_000))

        fallback_candidate = PhotoMetadataTransformer().build_asset_candidate(
            path=filename_photo.resolve(),
            metadata={},
            fallback_exif=PhotoExifMetadata(
                timestamp=datetime(2024, 4, 5, 6, 7, 8, tzinfo=UTC),
                latitude=11.5,
                longitude=12.5,
            ),
        )

        assert fallback_candidate.timestamp == datetime(2024, 4, 5, 6, 7, 8, tzinfo=UTC)
        assert fallback_candidate.latitude == 11.5
        assert fallback_candidate.longitude == 12.5
        assert fallback_candidate.metadata_json is not None
        assert (
            fallback_candidate.metadata_json["resolution"]["timestamp"]
            == "fallback_exif"
        )
        assert fallback_candidate.metadata_json["resolution"]["gps"] == "fallback_exif"

        filename_candidate = PhotoMetadataTransformer().build_asset_candidate(
            path=filename_photo.resolve(),
            metadata={},
            fallback_exif=PhotoExifMetadata(
                timestamp=None,
                latitude=None,
                longitude=None,
            ),
        )
        assert filename_candidate.timestamp == datetime(2023, 3, 4, 5, 6, 7, tzinfo=UTC)
        assert filename_candidate.metadata_json is not None
        assert filename_candidate.metadata_json["resolution"]["timestamp"] == "filename"

        plain_photo = workspace_root / "plain.jpg"
        plain_photo.write_bytes(b"photo")
        os.utime(plain_photo, (1_720_000_001, 1_720_000_001))

        mtime_candidate = PhotoMetadataTransformer().build_asset_candidate(
            path=plain_photo.resolve(),
            metadata={},
            fallback_exif=PhotoExifMetadata(
                timestamp=None,
                latitude=None,
                longitude=None,
            ),
        )
        assert mtime_candidate.timestamp == datetime.fromtimestamp(
            1_720_000_001,
            tz=UTC,
        )
        assert mtime_candidate.metadata_json is not None
        assert mtime_candidate.metadata_json["resolution"]["timestamp"] == "mtime"
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_photo_metadata_transformer_prefers_full_hierarchy_path_over_truncated_suffix_duplicate() -> (
    None
):
    workspace_root = _create_workspace_dir(prefix="photo-transform-hierarchy-suffix")
    try:
        photo_path = workspace_root / "image.jpg"
        photo_path.write_bytes(b"photo")

        candidate = PhotoMetadataTransformer().build_asset_candidate(
            path=photo_path.resolve(),
            metadata={
                "XMP:Subject": ["Weichering"],
                "XMP:HierarchicalSubject": [
                    "Deutschland|Weichering",
                    "WO|Deutschland|Weichering",
                ],
            },
            fallback_exif=PhotoExifMetadata(
                timestamp=datetime(2024, 1, 2, 3, 4, 5, tzinfo=UTC),
                latitude=None,
                longitude=None,
            ),
        )

        assert candidate.tag_paths == (
            "WO",
            "WO|Deutschland",
            "WO|Deutschland|Weichering",
        )
        assert candidate.asset_tag_paths == ("WO|Deutschland|Weichering",)
        assert candidate.metadata_json is not None
        assert candidate.metadata_json["hierarchical_subjects"] == [
            "WO|Deutschland|Weichering"
        ]
        assert candidate.metadata_json["linked_tag_paths"] == [
            "WO|Deutschland|Weichering"
        ]
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def _create_workspace_dir(*, prefix: str) -> Path:
    workspace_root = Path("var") / f"{prefix}-{uuid4().hex}"
    workspace_root.mkdir(parents=True, exist_ok=False)
    return workspace_root
