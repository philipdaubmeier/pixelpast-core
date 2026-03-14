"""Unit tests for the photo metadata fetch layer."""

from __future__ import annotations

import subprocess
import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from pixelpast.ingestion.photos.connector import PhotoConnector
from pixelpast.ingestion.photos.fetch import (
    PhotoMetadataFetcher,
    count_photo_metadata_batches,
)


def test_photo_connector_extract_metadata_delegates_to_fetcher() -> None:
    workspace_root = _create_workspace_dir(prefix="photo-fetch-delegate")
    try:
        path = workspace_root / "image.jpg"
        path.write_bytes(b"photo")
        resolved_path = path.resolve().as_posix()

        fetcher = _RecordingFetcher(
            result={resolved_path: {"SourceFile": resolved_path, "XMP:Title": "image"}}
        )
        metadata_by_path = PhotoConnector(
            metadata_fetcher=fetcher
        ).extract_metadata_by_path(paths=[path])

        assert fetcher.calls == [[path]]
        assert metadata_by_path[resolved_path]["XMP:Title"] == "image"
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_photo_metadata_fetcher_splits_timed_out_batches_until_single_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_root = _create_workspace_dir(prefix="photo-fetch-timeout")
    try:
        paths: list[Path] = []
        for name in ("a.jpg", "b.jpg", "c.jpg", "d.jpg"):
            path = workspace_root / name
            path.write_bytes(b"photo")
            paths.append(path.resolve())

        calls: list[tuple[str, ...]] = []

        def fake_run_exiftool_json(*, paths: list[Path]) -> list[dict[str, str]]:
            calls.append(tuple(path.name for path in paths))
            if any(path.name in {"b.jpg", "c.jpg"} for path in paths):
                raise subprocess.TimeoutExpired(cmd="exiftool", timeout=120)
            return [{"SourceFile": path.as_posix(), "XMP:Title": path.stem} for path in paths]

        monkeypatch.setattr(
            "pixelpast.ingestion.photos.fetch._run_exiftool_json",
            fake_run_exiftool_json,
        )

        metadata_by_path = PhotoMetadataFetcher().extract_metadata_by_path(paths=paths)

        assert calls == [
            ("a.jpg",),
            ("b.jpg", "c.jpg", "d.jpg"),
            ("b.jpg",),
            ("c.jpg", "d.jpg"),
            ("c.jpg",),
            ("d.jpg",),
        ]
        assert metadata_by_path[paths[0].as_posix()]["XMP:Title"] == "a"
        assert metadata_by_path[paths[1].as_posix()] == {"SourceFile": paths[1].as_posix()}
        assert metadata_by_path[paths[2].as_posix()] == {"SourceFile": paths[2].as_posix()}
        assert metadata_by_path[paths[3].as_posix()]["XMP:Title"] == "d"
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_photo_metadata_fetcher_wraps_missing_exiftool_as_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_root = _create_workspace_dir(prefix="photo-fetch-missing-exiftool")
    try:
        path = workspace_root / "image.jpg"
        path.write_bytes(b"photo")

        monkeypatch.setattr(
            "pixelpast.ingestion.photos.fetch.shutil.which",
            lambda executable: None,
        )

        with pytest.raises(
            RuntimeError,
            match="Photo ingestion requires exiftool to be installed and callable.",
        ):
            PhotoMetadataFetcher().extract_metadata_by_path(paths=[path])
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_count_photo_metadata_batches_keeps_first_file_as_singleton_batch() -> None:
    assert count_photo_metadata_batches(0) == 0
    assert count_photo_metadata_batches(1) == 1
    assert count_photo_metadata_batches(2) == 2
    assert count_photo_metadata_batches(86) == 2
    assert count_photo_metadata_batches(87) == 3
    assert count_photo_metadata_batches(88) == 3


class _RecordingFetcher:
    def __init__(self, *, result: dict[str, dict[str, str]]) -> None:
        self.calls: list[list[Path]] = []
        self._result = result

    def extract_metadata_by_path(self, *, paths: list[Path], on_batch_progress=None):
        del on_batch_progress
        self.calls.append(paths)
        return self._result


def _create_workspace_dir(*, prefix: str) -> Path:
    workspace_root = Path("var") / f"{prefix}-{uuid4().hex}"
    workspace_root.mkdir(parents=True, exist_ok=False)
    return workspace_root
