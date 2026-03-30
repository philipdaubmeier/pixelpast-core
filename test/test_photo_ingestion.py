"""Photo ingestion connector and service tests."""

from __future__ import annotations

import os
import subprocess
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from pixelpast.ingestion.photos import (
    PhotoAssetCandidate,
    PhotoConnector,
    PhotoDiscoveryError,
    PhotoExifMetadata,
    PhotoIngestionRunCoordinator,
    PhotoIngestionService,
    PhotoMetadataBatchProgress,
    PhotoPersonCandidate,
)
from pixelpast.ingestion.photos.discovery import PhotoFileDiscoverer
from pixelpast.persistence.models import (
    Asset,
    AssetPerson,
    AssetTag,
    JobRun,
    Person,
    Source,
    Tag,
)
from pixelpast.persistence.repositories.canonical import AssetRepository
from pixelpast.shared.progress import build_initial_job_progress_payload
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import Settings


def test_photo_fixture_ingestion_persists_rich_metadata_and_relationships() -> None:
    workspace_root = _create_workspace_dir(prefix="photo-fixtures")
    runtime = None
    try:
        photos_root = _copy_photo_fixtures(workspace_root=workspace_root)
        runtime = _create_runtime(
            workspace_root=workspace_root,
            photos_root=photos_root,
        )

        result = PhotoIngestionService().ingest(runtime=runtime)

        assert result.processed_asset_count == 3
        assert result.error_count == 0
        assert result.status == "completed"
        assert result.discovered_file_count == 3
        assert result.analyzed_file_count == 3
        assert result.analysis_failed_file_count == 0
        assert result.assets_persisted == 3
        assert result.inserted_asset_count == 3
        assert result.updated_asset_count == 0
        assert result.unchanged_asset_count == 0
        assert result.skipped_asset_count == 0
        assert result.missing_from_source_count == 0
        assert result.metadata_batches_submitted == 2
        assert result.metadata_batches_completed == 2

        with runtime.session_factory() as session:
            assets = list(
                session.execute(select(Asset).order_by(Asset.external_id)).scalars()
            )
            people = list(
                session.execute(select(Person).order_by(Person.name)).scalars()
            )
            tags = list(session.execute(select(Tag).order_by(Tag.path)).scalars())
            asset_tags = list(session.execute(select(AssetTag)).scalars())
            asset_people = list(session.execute(select(AssetPerson)).scalars())

        assets_by_name = {Path(asset.external_id).name: asset for asset in assets}
        people_by_name = {person.name: person for person in people}
        tags_by_path = {tag.path: tag for tag in tags}
        asset_tag_paths_by_name = _collect_asset_tag_paths(
            assets=assets,
            tags=tags,
            asset_tags=asset_tags,
        )
        asset_person_names_by_name = _collect_asset_person_names(
            assets=assets,
            people=people,
            asset_people=asset_people,
        )

        expected_timestamp = datetime(2020, 1, 1, 2, 3, 40, tzinfo=UTC)
        assert set(assets_by_name) == {
            "monalisa-1.jpg",
            "monalisa-2.jpg",
            "monalisa-3.jpg",
        }
        assert assets_by_name["monalisa-1.jpg"].summary == "Title 1"
        assert assets_by_name["monalisa-2.jpg"].summary == "Title 2"
        assert assets_by_name["monalisa-3.jpg"].summary == "Title 3 äöüßÄÖÜ"
        assert all(asset.timestamp == expected_timestamp for asset in assets)
        assert assets_by_name["monalisa-1.jpg"].latitude == pytest.approx(
            48.8618924166667
        )
        assert assets_by_name["monalisa-1.jpg"].longitude == pytest.approx(
            2.33588663333333
        )
        assert assets_by_name["monalisa-2.jpg"].latitude == pytest.approx(
            48.8603977388889
        )
        assert assets_by_name["monalisa-2.jpg"].longitude == pytest.approx(
            2.33458610833333
        )
        assert assets_by_name["monalisa-3.jpg"].latitude == pytest.approx(
            48.8603837361111
        )
        assert assets_by_name["monalisa-3.jpg"].longitude == pytest.approx(
            2.33856171111111
        )

        leonardo = people_by_name["Leonardo da Vinci"]
        assert leonardo.path is None
        assert {asset.creator_person_id for asset in assets} == {leonardo.id}

        assert people_by_name["John Doe"].path == "who|Persons|John Doe"
        assert people_by_name["Mona Lisa"].path == "who|Persons|Mona Lisa"
        assert len(people) == 3

        expected_tag_paths = {
            "events",
            "events|vacation",
            "events|vacation|Italy",
            "events|vacation|Italy|San Marino",
            "events|vacation|München",
            "events|wedding",
            "who",
            "who|Persons",
            "who|Persons|John Doe",
            "who|Persons|Mona Lisa",
        }
        assert set(tags_by_path) == expected_tag_paths
        assert tags_by_path["events|vacation|München"].label == "München"
        assert tags_by_path["events|vacation|Italy|San Marino"].label == "San Marino"
        assert tags_by_path["who|Persons|Mona Lisa"].label == "Mona Lisa"

        assert asset_tag_paths_by_name["monalisa-1.jpg"] == {
            "events",
            "events|vacation",
            "events|vacation|München",
        }
        assert asset_tag_paths_by_name["monalisa-2.jpg"] == {
            "events",
            "events|vacation",
            "events|vacation|Italy",
            "events|vacation|Italy|San Marino",
        }
        assert asset_tag_paths_by_name["monalisa-3.jpg"] == {
            "events",
            "events|vacation",
            "events|vacation|München",
            "events|wedding",
        }

        assert asset_person_names_by_name["monalisa-1.jpg"] == {"Mona Lisa"}
        assert asset_person_names_by_name["monalisa-2.jpg"] == {"John Doe", "Mona Lisa"}
        assert asset_person_names_by_name["monalisa-3.jpg"] == {"John Doe", "Mona Lisa"}
        assert len(asset_people) == 5

        metadata_json = assets_by_name["monalisa-3.jpg"].metadata_json
        assert metadata_json is not None
        assert metadata_json["resolution"]["title"] == "XMP-dc:Title"
        assert metadata_json["resolution"]["creator"] == "XMP-dc:Creator"
        assert metadata_json["resolution"]["timestamp"] == "ExifIFD:DateTimeOriginal"
        assert metadata_json["linked_tag_paths"] == [
            "events|vacation|München",
            "events",
            "events|vacation",
            "events|wedding",
        ]
        assert metadata_json["persons"] == [
            {"name": "John Doe", "path": "who|Persons|John Doe"},
            {"name": "Mona Lisa", "path": "who|Persons|Mona Lisa"},
        ]
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_photo_ingestion_with_fixtures_is_idempotent() -> None:
    workspace_root = _create_workspace_dir(prefix="photo-idempotent")
    runtime = None
    try:
        photos_root = _copy_photo_fixtures(workspace_root=workspace_root)
        runtime = _create_runtime(
            workspace_root=workspace_root,
            photos_root=photos_root,
        )

        first_result = PhotoIngestionService().ingest(runtime=runtime)
        second_result = PhotoIngestionService().ingest(runtime=runtime)

        assert first_result.processed_asset_count == 3
        assert second_result.processed_asset_count == 3
        assert first_result.status == "completed"
        assert second_result.status == "completed"
        assert first_result.inserted_asset_count == 3
        assert first_result.updated_asset_count == 0
        assert first_result.unchanged_asset_count == 0
        assert second_result.inserted_asset_count == 0
        assert second_result.updated_asset_count == 0
        assert second_result.unchanged_asset_count == 3
        assert second_result.missing_from_source_count == 0

        with runtime.session_factory() as session:
            assets = list(session.execute(select(Asset)).scalars())
            job_runs = list(
                session.execute(select(JobRun).order_by(JobRun.id)).scalars()
            )
            people = list(session.execute(select(Person)).scalars())
            tags = list(session.execute(select(Tag)).scalars())
            asset_tags = list(session.execute(select(AssetTag)).scalars())
            asset_people = list(session.execute(select(AssetPerson)).scalars())
            sources = list(session.execute(select(Source)).scalars())

        assert len(assets) == 3
        assert len(job_runs) == 2
        assert [run.type for run in job_runs] == ["ingest", "ingest"]
        assert [run.job for run in job_runs] == ["photos", "photos"]
        assert [run.status for run in job_runs] == ["completed", "completed"]
        assert len(people) == 3
        assert len(tags) == 10
        assert len(asset_tags) == 11
        assert len(asset_people) == 5
        assert len(sources) == 1
        assert sources[0].config == {"root_path": photos_root.resolve().as_posix()}
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_photo_connector_applies_deterministic_metadata_precedence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_root = _create_workspace_dir(prefix="photo-precedence")
    try:
        photos_root = workspace_root / "photos"
        photos_root.mkdir()
        photo_path = photos_root / "IMG_20240102_030405.jpg"
        photo_path.write_bytes(b"not-a-real-image")

        monkeypatch.setattr(
            "pixelpast.ingestion.photos.connector.extract_photo_tool_metadata",
            lambda path: {
                "XMP-dc:Title": "XMP Title",
                "IPTC:ObjectName": "IPTC Title",
                "XMP-dc:Creator": "XMP Creator",
                "IPTC:By-line": "IPTC Creator",
                "IFD0:Artist": "EXIF Artist",
                "ExifIFD:DateTimeOriginal": "2020:01:01 02:03:40",
            },
        )
        monkeypatch.setattr(
            "pixelpast.ingestion.photos.connector.extract_photo_exif_metadata",
            lambda path: PhotoExifMetadata(
                timestamp=datetime(2024, 1, 2, 3, 4, 5, tzinfo=UTC),
                latitude=None,
                longitude=None,
            ),
        )

        candidate = PhotoConnector().build_asset_candidate(
            root=photos_root,
            path=photo_path,
        )

        assert candidate.summary == "XMP Title"
        assert candidate.creator_name == "XMP Creator"
        assert candidate.timestamp == datetime(2020, 1, 1, 2, 3, 40, tzinfo=UTC)
        assert candidate.metadata_json is not None
        assert candidate.metadata_json["resolution"]["title"] == "XMP-dc:Title"
        assert candidate.metadata_json["resolution"]["creator"] == "XMP-dc:Creator"
        assert (
            candidate.metadata_json["resolution"]["timestamp"]
            == "ExifIFD:DateTimeOriginal"
        )
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_photo_file_discoverer_filters_supported_extensions_and_reports_stable_progress() -> None:
    workspace_root = _create_workspace_dir(prefix="photo-discovery")
    try:
        photos_root = workspace_root / "photos"
        nested_root = photos_root / "nested"
        photos_root.mkdir()
        nested_root.mkdir()
        (photos_root / "z-last.png").write_bytes(b"photo")
        (nested_root / "a-first.jpeg").write_bytes(b"photo")
        (nested_root / "skip.txt").write_text("ignore", encoding="utf-8")
        (photos_root / "also-skip.mp4").write_bytes(b"video")

        observed_progress: list[tuple[str, int]] = []

        paths = PhotoFileDiscoverer().discover_paths(
            photos_root,
            on_path_discovered=lambda path, count: observed_progress.append(
                (path.name, count)
            ),
        )

        assert [path.name for path in paths] == ["a-first.jpeg", "z-last.png"]
        assert observed_progress == [("a-first.jpeg", 1), ("z-last.png", 2)]
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_photo_connector_discover_convenience_method_delegates_to_override_points() -> None:
    workspace_root = _create_workspace_dir(prefix="photo-discover-facade")
    try:
        photos_root = workspace_root / "photos"
        photos_root.mkdir()
        resolved_root = photos_root.resolve()

        result = _ConvenienceDiscoverConnector().discover(photos_root)

        assert [asset.summary for asset in result.assets] == ["first", "second"]
        assert result.errors == [
            PhotoDiscoveryError(
                path=resolved_root / "broken.jpg",
                message="bad metadata",
            )
        ]
        assert result.discovered_paths == (
            resolved_root / "first.jpg",
            resolved_root / "broken.jpg",
            resolved_root / "second.jpg",
        )
        assert result.metadata_batch_count == 2
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_photo_ingestion_handles_empty_directories() -> None:
    workspace_root = _create_workspace_dir(prefix="photo-empty")
    runtime = None
    try:
        photos_root = workspace_root / "photos"
        photos_root.mkdir()

        runtime = _create_runtime(
            workspace_root=workspace_root,
            photos_root=photos_root,
        )
        result = PhotoIngestionService().ingest(runtime=runtime)

        assert result.processed_asset_count == 0
        assert result.error_count == 0
        assert result.status == "completed"
        assert result.discovered_file_count == 0
        assert result.analyzed_file_count == 0
        assert result.analysis_failed_file_count == 0
        assert result.assets_persisted == 0
        assert result.inserted_asset_count == 0
        assert result.updated_asset_count == 0
        assert result.unchanged_asset_count == 0
        assert result.skipped_asset_count == 0
        assert result.missing_from_source_count == 0

        with runtime.session_factory() as session:
            assets = list(session.execute(select(Asset)).scalars())
            job_runs = list(session.execute(select(JobRun)).scalars())

        assert assets == []
        assert len(job_runs) == 1
        assert job_runs[0].type == "ingest"
        assert job_runs[0].job == "photos"
        assert job_runs[0].status == "completed"
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_photo_ingestion_fails_fast_when_exiftool_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_root = _create_workspace_dir(prefix="photo-missing-exiftool")
    runtime = None
    try:
        photos_root = workspace_root / "photos"
        photos_root.mkdir()
        (photos_root / "image.jpg").write_bytes(b"photo")

        runtime = _create_runtime(
            workspace_root=workspace_root,
            photos_root=photos_root,
        )

        monkeypatch.setattr(
            "pixelpast.ingestion.photos.fetch.shutil.which",
            lambda executable: None,
        )

        with pytest.raises(
            RuntimeError,
            match="Photo ingestion requires exiftool to be installed and callable.",
        ):
            PhotoIngestionService().ingest(runtime=runtime)

        with runtime.session_factory() as session:
            assets = list(session.execute(select(Asset)).scalars())
            job_runs = list(session.execute(select(JobRun)).scalars())

        assert assets == []
        assert len(job_runs) == 1
        assert job_runs[0].type == "ingest"
        assert job_runs[0].job == "photos"
        assert job_runs[0].status == "failed"
        assert job_runs[0].phase == "metadata extraction"
        assert job_runs[0].last_heartbeat_at is not None
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_photo_ingestion_requires_media_thumb_root_before_run_creation() -> None:
    workspace_root = _create_workspace_dir(prefix="photo-missing-thumb-root")
    runtime = None
    try:
        photos_root = workspace_root / "photos"
        photos_root.mkdir()
        (photos_root / "image.jpg").write_bytes(b"photo")
        runtime = create_runtime_context(
            settings=Settings(
                database_url=f"sqlite:///{(workspace_root / 'pixelpast.db').as_posix()}",
                photos_root=photos_root,
                media_thumb_root=None,
            )
        )
        initialize_database(runtime)

        with pytest.raises(
            ValueError,
            match="PIXELPAST_MEDIA_THUMB_ROOT",
        ):
            PhotoIngestionService().ingest(runtime=runtime)

        with runtime.session_factory() as session:
            assets = list(session.execute(select(Asset)).scalars())
            job_runs = list(session.execute(select(JobRun)).scalars())

        assert assets == []
        assert job_runs == []
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_photo_connector_splits_timed_out_metadata_batches_until_single_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_root = _create_workspace_dir(prefix="photo-batch-timeout")
    try:
        photos_root = workspace_root / "photos"
        photos_root.mkdir()
        paths = []
        for name in ("a.jpg", "b.jpg", "c.jpg", "d.jpg"):
            path = photos_root / name
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

        metadata_by_path = PhotoConnector().extract_metadata_by_path(paths=paths)

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


def test_photo_connector_partial_failure_is_reported_and_persisted() -> None:
    workspace_root = _create_workspace_dir(prefix="photo-partial")
    runtime = None
    try:
        photos_root = workspace_root / "photos"
        photos_root.mkdir()

        runtime = _create_runtime(
            workspace_root=workspace_root,
            photos_root=photos_root,
        )
        result = PhotoIngestionService(connector=_PartialFailureConnector()).ingest(
            runtime=runtime
        )

        assert result.processed_asset_count == 1
        assert result.error_count == 1
        assert result.status == "partial_failure"
        assert result.discovered_file_count == 2
        assert result.analyzed_file_count == 1
        assert result.analysis_failed_file_count == 1
        assert result.assets_persisted == 1
        assert result.inserted_asset_count == 1
        assert result.updated_asset_count == 0
        assert result.unchanged_asset_count == 0
        assert result.skipped_asset_count == 0

        with runtime.session_factory() as session:
            assets = list(session.execute(select(Asset)).scalars())
            job_run = session.execute(select(JobRun)).scalar_one()

        assert len(assets) == 1
        assert job_run.type == "ingest"
        assert job_run.job == "photos"
        assert job_run.status == "partial_failure"
        assert job_run.phase == "finalization"
        assert job_run.progress_json is not None
        assert job_run.progress_json["failed"] == 1
        assert job_run.progress_json["inserted"] == 1
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_photo_ingestion_marks_run_failed_and_rolls_back_assets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_root = _create_workspace_dir(prefix="photo-failed-run")
    runtime = None
    try:
        photos_root = workspace_root / "photos"
        photos_root.mkdir()

        runtime = _create_runtime(
            workspace_root=workspace_root,
            photos_root=photos_root,
        )

        call_count = 0
        original_asset_upsert = AssetRepository.upsert

        def fail_on_second_upsert(self, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("boom")
            return original_asset_upsert(self, **kwargs)

        monkeypatch.setattr(
            AssetRepository,
            "upsert",
            fail_on_second_upsert,
        )

        with pytest.raises(RuntimeError, match="boom"):
            PhotoIngestionService(connector=_FatalFailureConnector()).ingest(
                runtime=runtime
            )

        with runtime.session_factory() as session:
            assets = list(session.execute(select(Asset)).scalars())
            job_runs = list(
                session.execute(select(JobRun).order_by(JobRun.id)).scalars()
            )

        assert assets == []
        assert len(job_runs) == 1
        assert job_runs[0].type == "ingest"
        assert job_runs[0].job == "photos"
        assert job_runs[0].status == "failed"
        assert job_runs[0].finished_at is not None
        assert job_runs[0].phase == "canonical persistence"
        assert job_runs[0].last_heartbeat_at is not None
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_photo_ingestion_marks_existing_assets_updated_when_canonical_state_changes() -> None:
    workspace_root = _create_workspace_dir(prefix="photo-updated")
    runtime = None
    try:
        photos_root = workspace_root / "photos"
        photos_root.mkdir()
        photo_path = photos_root / "image.jpg"
        photo_path.write_bytes(b"photo")

        runtime = _create_runtime(
            workspace_root=workspace_root,
            photos_root=photos_root,
        )
        first_result = PhotoIngestionService(
            connector=_SingleAssetConnector(summary="Version 1")
        ).ingest(runtime=runtime)
        second_result = PhotoIngestionService(
            connector=_SingleAssetConnector(summary="Version 2")
        ).ingest(runtime=runtime)

        assert first_result.inserted_asset_count == 1
        assert second_result.inserted_asset_count == 0
        assert second_result.updated_asset_count == 1
        assert second_result.unchanged_asset_count == 0

        with runtime.session_factory() as session:
            asset = session.execute(select(Asset)).scalar_one()

        assert asset.summary == "Version 2"
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_photo_ingestion_surfaces_missing_from_source_without_deleting_assets() -> None:
    workspace_root = _create_workspace_dir(prefix="photo-missing-from-source")
    runtime = None
    try:
        photos_root = workspace_root / "photos"
        photos_root.mkdir()
        first_path = photos_root / "first.jpg"
        second_path = photos_root / "second.jpg"
        first_path.write_bytes(b"photo")
        second_path.write_bytes(b"photo")

        runtime = _create_runtime(
            workspace_root=workspace_root,
            photos_root=photos_root,
        )
        connector = _DirectoryBackedConnector()
        first_result = PhotoIngestionService(connector=connector).ingest(runtime=runtime)
        second_path.unlink()

        second_result = PhotoIngestionService(connector=connector).ingest(runtime=runtime)

        assert first_result.missing_from_source_count == 0
        assert second_result.missing_from_source_count == 1
        assert second_result.inserted_asset_count == 0
        assert second_result.updated_asset_count == 0
        assert second_result.unchanged_asset_count == 1

        with runtime.session_factory() as session:
            assets = list(
                session.execute(select(Asset).order_by(Asset.external_id)).scalars()
            )

        assert len(assets) == 2
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_photo_ingestion_persists_heartbeat_updates_during_a_long_running_run() -> None:
    workspace_root = _create_workspace_dir(prefix="photo-heartbeat")
    runtime = None
    try:
        photos_root = workspace_root / "photos"
        photos_root.mkdir()
        for index in range(3):
            (photos_root / f"image-{index}.jpg").write_bytes(b"photo")

        runtime = _create_runtime(
            workspace_root=workspace_root,
            photos_root=photos_root,
        )
        clock = _FakeClock()
        observed_heartbeats: list[tuple[str, int, datetime | None]] = []

        def capture_progress(snapshot) -> None:
            if not snapshot.heartbeat_written or snapshot.phase != "filesystem discovery":
                return
            if snapshot.completed < 2:
                return
            with runtime.session_factory() as session:
                job_run = session.execute(select(JobRun)).scalar_one()
            observed_heartbeats.append(
                (
                    job_run.phase or "",
                    job_run.progress_json["completed"],
                    job_run.last_heartbeat_at,
                )
            )

        result = PhotoIngestionService(
            connector=_HeartbeatConnector(clock=clock),
            heartbeat_interval_seconds=10.0,
            now_factory=clock.now,
            monotonic_factory=clock.monotonic,
        ).ingest(
            runtime=runtime,
            progress_callback=capture_progress,
        )

        assert result.status == "completed"
        assert observed_heartbeats
        assert observed_heartbeats[-1][0] == "filesystem discovery"
        assert observed_heartbeats[-1][1] >= 2
        assert observed_heartbeats[-1][2] == clock.now()

        with runtime.session_factory() as session:
            job_run = session.execute(select(JobRun)).scalar_one()

        assert job_run.type == "ingest"
        assert job_run.job == "photos"
        assert job_run.status == "completed"
        assert job_run.last_heartbeat_at == clock.now()
        assert job_run.progress_json["completed"] == 1
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_photo_ingestion_reports_metadata_phase_progress_after_completed_batches() -> None:
    workspace_root = _create_workspace_dir(prefix="photo-metadata-progress")
    runtime = None
    try:
        photos_root = workspace_root / "photos"
        photos_root.mkdir()
        for name in ("image-0.jpg", "image-1.jpg", "image-2.jpg"):
            (photos_root / name).write_bytes(b"photo")

        runtime = _create_runtime(
            workspace_root=workspace_root,
            photos_root=photos_root,
        )
        observed_completed: list[int] = []

        def capture_progress(snapshot) -> None:
            if snapshot.event != "progress" or snapshot.phase != "metadata extraction":
                return
            observed_completed.append(snapshot.completed)

        result = PhotoIngestionService(
            connector=_MetadataBatchProgressConnector()
        ).ingest(
            runtime=runtime,
            progress_callback=capture_progress,
        )

        assert result.status == "completed"
        assert observed_completed == [0, 1, 1, 3, 3, 3, 3, 3]
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_photo_ingestion_run_lifecycle_uses_authoritative_initial_progress_shape() -> None:
    workspace_root = _create_workspace_dir(prefix="photo-lifecycle-bootstrap")
    runtime = None
    try:
        photos_root = workspace_root / "photos"
        photos_root.mkdir()
        runtime = _create_runtime(
            workspace_root=workspace_root,
            photos_root=photos_root,
        )

        run_id = PhotoIngestionRunCoordinator().create_run(
            runtime=runtime,
            resolved_root=photos_root.resolve(),
        )

        with runtime.session_factory() as session:
            job_run = session.execute(select(JobRun)).scalar_one()
            source = session.execute(select(Source)).scalar_one()

        assert job_run.id == run_id
        assert job_run.type == "ingest"
        assert job_run.job == "photos"
        assert job_run.status == "running"
        assert job_run.mode == "full"
        assert job_run.phase == "initializing"
        assert job_run.progress_json == build_initial_job_progress_payload()
        assert source.name == "Photos"
        assert source.type == "photos"
        assert source.config == {"root_path": photos_root.resolve().as_posix()}
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_photo_ingestion_run_lifecycle_counts_missing_from_source_without_mutation() -> None:
    workspace_root = _create_workspace_dir(prefix="photo-lifecycle-missing")
    runtime = None
    try:
        photos_root = workspace_root / "photos"
        photos_root.mkdir()
        kept_path = photos_root / "kept.jpg"
        missing_path = photos_root / "missing.jpg"
        kept_path.write_bytes(b"photo")

        runtime = _create_runtime(
            workspace_root=workspace_root,
            photos_root=photos_root,
        )
        source_id = PhotoIngestionRunCoordinator().get_source_id(
            runtime=runtime,
            resolved_root=photos_root.resolve(),
        )

        with runtime.session_factory() as session:
            repository = AssetRepository(session)
            for path in (kept_path, missing_path):
                repository.upsert(
                    source_id=source_id,
                    external_id=path.resolve().as_posix(),
                    media_type="photo",
                    timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                    summary=None,
                    latitude=None,
                    longitude=None,
                    creator_person_id=None,
                    metadata_json={},
                )
            session.commit()

        with runtime.session_factory() as session:
            repository = AssetRepository(session)
            missing_count = PhotoIngestionRunCoordinator().count_missing_from_source(
                asset_repository=repository,
                source_id=source_id,
                resolved_root=photos_root.resolve(),
                discovered_paths=[kept_path.resolve()],
            )
            assets = list(session.execute(select(Asset).order_by(Asset.external_id)).scalars())

        assert missing_count == 1
        assert len(assets) == 2
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_photo_connector_builds_filename_and_mtime_fallbacks() -> None:
    workspace_root = _create_workspace_dir(prefix="photo-fallbacks")
    try:
        photos_root = workspace_root / "photos"
        photos_root.mkdir()

        connector = PhotoConnector()

        filename_photo = photos_root / "IMG_20230304_050607.jpeg"
        filename_photo.write_bytes(b"photo")
        filename_candidate = connector.build_asset_candidate(
            root=photos_root,
            path=filename_photo,
            metadata={},
        )

        mtime_photo = photos_root / "plain.heic"
        mtime_photo.write_bytes(b"photo")
        os.utime(mtime_photo, (1_720_000_000, 1_720_000_000))
        mtime_candidate = connector.build_asset_candidate(
            root=photos_root,
            path=mtime_photo,
            metadata={},
        )

        assert filename_candidate.timestamp == datetime(2023, 3, 4, 5, 6, 7, tzinfo=UTC)
        assert filename_candidate.summary is None
        assert filename_candidate.creator_name is None
        assert filename_candidate.tag_paths == ()
        assert filename_candidate.asset_tag_paths == ()
        assert filename_candidate.persons == ()
        assert filename_candidate.metadata_json is not None
        assert filename_candidate.metadata_json["resolution"]["timestamp"] == "filename"

        assert mtime_candidate.timestamp == datetime.fromtimestamp(
            1_720_000_000,
            tz=UTC,
        )
        assert mtime_candidate.metadata_json is not None
        assert mtime_candidate.metadata_json["resolution"]["timestamp"] == "mtime"
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_asset_repository_generates_and_preserves_short_id() -> None:
    workspace_root = _create_workspace_dir(prefix="photo-short-id-upsert")
    runtime = None
    try:
        photos_root = workspace_root / "photos"
        photos_root.mkdir()
        runtime = _create_runtime(
            workspace_root=workspace_root,
            photos_root=photos_root,
        )
        source_id = PhotoIngestionRunCoordinator().get_source_id(
            runtime=runtime,
            resolved_root=photos_root.resolve(),
        )

        with runtime.session_factory() as session:
            repository = AssetRepository(session)
            inserted = repository.upsert(
                source_id=source_id,
                external_id="photo-1",
                media_type="photo",
                timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                summary="first",
                latitude=None,
                longitude=None,
                creator_person_id=None,
                metadata_json={},
            )
            inserted_short_id = inserted.asset.short_id
            updated = repository.upsert(
                source_id=source_id,
                external_id="photo-1",
                media_type="photo",
                timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                summary="renamed",
                latitude=None,
                longitude=None,
                creator_person_id=None,
                metadata_json={"updated": True},
            )
            fetched = repository.get_by_short_id(short_id=inserted_short_id)
            session.commit()

        assert inserted.status == "inserted"
        assert len(inserted_short_id) == 8
        assert updated.status == "updated"
        assert updated.asset.short_id == inserted_short_id
        assert fetched is not None
        assert fetched.external_id == "photo-1"
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_asset_repository_retries_when_generated_short_id_collides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_root = _create_workspace_dir(prefix="photo-short-id-collision")
    runtime = None
    try:
        photos_root = workspace_root / "photos"
        photos_root.mkdir()
        runtime = _create_runtime(
            workspace_root=workspace_root,
            photos_root=photos_root,
        )
        source_id = PhotoIngestionRunCoordinator().get_source_id(
            runtime=runtime,
            resolved_root=photos_root.resolve(),
        )

        generated_ids = iter(("AAAAAAAA", "BBBBBBBB"))
        monkeypatch.setattr(
            "pixelpast.persistence.repositories.canonical.AssetRepository._allocate_short_id",
            lambda self: next(generated_ids),
        )

        with runtime.session_factory() as session:
            repository = AssetRepository(session)
            session.add(
                Asset(
                    short_id="AAAAAAAA",
                    source_id=source_id,
                    external_id="existing-photo",
                    media_type="photo",
                    timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                    latitude=None,
                    longitude=None,
                    metadata_json={},
                )
            )
            session.flush()

            inserted = repository.upsert(
                source_id=source_id,
                external_id="photo-2",
                media_type="photo",
                timestamp=datetime(2024, 1, 2, tzinfo=UTC),
                summary="second",
                latitude=None,
                longitude=None,
                creator_person_id=None,
                metadata_json={},
            )
            session.commit()

        assert inserted.status == "inserted"
        assert inserted.asset.short_id == "BBBBBBBB"
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_asset_external_id_is_unique_at_database_level() -> None:
    workspace_root = _create_workspace_dir(prefix="photo-asset-unique")
    runtime = None
    try:
        photos_root = workspace_root / "photos"
        photos_root.mkdir()
        runtime = _create_runtime(
            workspace_root=workspace_root,
            photos_root=photos_root,
        )
        source_id = PhotoIngestionRunCoordinator().get_source_id(
            runtime=runtime,
            resolved_root=photos_root.resolve(),
        )

        with pytest.raises(IntegrityError):
            with runtime.session_factory() as session:
                session.add_all(
                    [
                        Asset(
                            source_id=source_id,
                            external_id="duplicate-id",
                            media_type="photo",
                            timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
                            latitude=None,
                            longitude=None,
                            metadata_json={},
                        ),
                        Asset(
                            source_id=source_id,
                            external_id="duplicate-id",
                            media_type="photo",
                            timestamp=datetime(2024, 1, 1, 1, 0, tzinfo=UTC),
                            latitude=None,
                            longitude=None,
                            metadata_json={},
                        ),
                    ]
                )
                session.commit()
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_source_type_and_name_are_unique_at_database_level() -> None:
    workspace_root = _create_workspace_dir(prefix="photo-source-unique")
    runtime = None
    try:
        photos_root = workspace_root / "photos"
        photos_root.mkdir()
        runtime = _create_runtime(
            workspace_root=workspace_root,
            photos_root=photos_root,
        )

        with pytest.raises(IntegrityError):
            with runtime.session_factory() as session:
                session.add_all(
                    [
                        Source(name="Photos", type="photos", config={}),
                        Source(name="Photos", type="photos", config={}),
                    ]
                )
                session.commit()
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_sources_can_share_type_when_name_differs() -> None:
    workspace_root = _create_workspace_dir(prefix="photo-source-shared-type")
    runtime = None
    try:
        photos_root = workspace_root / "photos"
        photos_root.mkdir()
        runtime = _create_runtime(
            workspace_root=workspace_root,
            photos_root=photos_root,
        )

        with runtime.session_factory() as session:
            session.add_all(
                [
                    Source(name="Photos A", type="photos", config={}),
                    Source(name="Photos B", type="photos", config={}),
                ]
            )
            session.commit()

            sources = list(
                session.execute(
                    select(Source).where(Source.type == "photos").order_by(Source.name)
                ).scalars()
            )

        assert [source.name for source in sources] == ["Photos A", "Photos B"]
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_source_external_id_is_unique_at_database_level_when_present() -> None:
    workspace_root = _create_workspace_dir(prefix="source-external-id-unique")
    runtime = None
    try:
        photos_root = workspace_root / "photos"
        photos_root.mkdir()
        runtime = _create_runtime(
            workspace_root=workspace_root,
            photos_root=photos_root,
        )

        with pytest.raises(IntegrityError):
            with runtime.session_factory() as session:
                session.add_all(
                    [
                        Source(
                            name="Calendar A",
                            type="calendar",
                            external_id="calendar-123",
                            config={},
                        ),
                        Source(
                            name="Calendar B",
                            type="calendar",
                            external_id="calendar-123",
                            config={},
                        ),
                    ]
                )
                session.commit()
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_sources_can_omit_external_id_without_regressing_photo_behavior() -> None:
    workspace_root = _create_workspace_dir(prefix="source-external-id-null")
    runtime = None
    try:
        photos_root = workspace_root / "photos"
        photos_root.mkdir()
        runtime = _create_runtime(
            workspace_root=workspace_root,
            photos_root=photos_root,
        )

        with runtime.session_factory() as session:
            session.add_all(
                [
                    Source(name="Photos A", type="photos", external_id=None, config={}),
                    Source(name="Photos B", type="photos", external_id=None, config={}),
                ]
            )
            session.commit()

            sources = list(
                session.execute(select(Source).order_by(Source.name)).scalars()
            )

        assert [source.name for source in sources] == ["Photos A", "Photos B"]
        assert [source.external_id for source in sources] == [None, None]
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


class _ConvenienceDiscoverConnector(PhotoConnector):
    """Test connector that freezes discover() delegation behavior."""

    def discover_paths(
        self,
        root: Path,
        *,
        on_path_discovered=None,
    ) -> list[Path]:
        del on_path_discovered
        return [root / "first.jpg", root / "broken.jpg", root / "second.jpg"]

    def extract_metadata_by_path(self, *, paths: list[Path], on_batch_progress=None):
        del on_batch_progress
        return {path.resolve().as_posix(): {"summary": path.stem} for path in paths}

    def build_asset_candidate(
        self,
        *,
        root: Path,
        path: Path,
        metadata=None,
    ) -> PhotoAssetCandidate:
        del root
        if path.name == "broken.jpg":
            raise RuntimeError("bad metadata")
        return PhotoAssetCandidate(
            external_id=path.resolve().as_posix(),
            media_type="photo",
            timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
            summary=metadata["summary"] if metadata is not None else None,
            latitude=None,
            longitude=None,
            creator_name=None,
            tag_paths=(),
            asset_tag_paths=(),
            persons=(),
            metadata_json={},
        )


class _PartialFailureConnector(PhotoConnector):
    """Test connector that simulates one successful asset and one failure."""

    def discover_paths(
        self,
        root: Path,
        *,
        on_path_discovered=None,
    ) -> list[Path]:
        paths = [root / "ok.jpg", root / "broken.jpg"]
        if on_path_discovered is not None:
            for index, path in enumerate(paths, start=1):
                on_path_discovered(path, index)
        return paths

    def extract_metadata_by_path(self, *, paths: list[Path], on_batch_progress=None):
        del paths, on_batch_progress
        return {}

    def build_asset_candidate(
        self,
        *,
        root: Path,
        path: Path,
        metadata=None,
    ) -> PhotoAssetCandidate:
        del root, metadata
        if path.name == "broken.jpg":
            raise RuntimeError("decode error")
        return PhotoAssetCandidate(
            external_id=path.resolve().as_posix(),
            media_type="photo",
            timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
            summary=None,
            latitude=None,
            longitude=None,
            creator_name=None,
            tag_paths=(),
            asset_tag_paths=(),
            persons=(),
            metadata_json={},
        )


class _FatalFailureConnector(PhotoConnector):
    """Test connector that triggers a failure during asset persistence."""

    def discover_paths(
        self,
        root: Path,
        *,
        on_path_discovered=None,
    ) -> list[Path]:
        paths = [root / "one.jpg", root / "two.jpg"]
        if on_path_discovered is not None:
            for index, path in enumerate(paths, start=1):
                on_path_discovered(path, index)
        return paths

    def extract_metadata_by_path(self, *, paths: list[Path], on_batch_progress=None):
        del paths, on_batch_progress
        return {}

    def build_asset_candidate(
        self,
        *,
        root: Path,
        path: Path,
        metadata=None,
    ) -> PhotoAssetCandidate:
        del root, metadata
        persons = (
            (PhotoPersonCandidate(name="Person A", path=None),)
            if path.name == "one.jpg"
            else ()
        )
        return PhotoAssetCandidate(
            external_id=path.resolve().as_posix(),
            media_type="photo",
            timestamp=datetime(2024, 1, 1, 0 if path.name == "one.jpg" else 1, 0, tzinfo=UTC),
            summary=None,
            latitude=None,
            longitude=None,
            creator_name=None,
            tag_paths=(),
            asset_tag_paths=(),
            persons=persons,
            metadata_json={},
        )


class _SingleAssetConnector(PhotoConnector):
    """Test connector that emits a single deterministic asset."""

    def __init__(self, *, summary: str) -> None:
        self._summary = summary

    def discover_paths(
        self,
        root: Path,
        *,
        on_path_discovered=None,
    ) -> list[Path]:
        path = root / "image.jpg"
        if on_path_discovered is not None:
            on_path_discovered(path, 1)
        return [path]

    def extract_metadata_by_path(self, *, paths: list[Path], on_batch_progress=None):
        del paths, on_batch_progress
        return {}

    def build_asset_candidate(
        self,
        *,
        root: Path,
        path: Path,
        metadata=None,
    ) -> PhotoAssetCandidate:
        del root, metadata
        return PhotoAssetCandidate(
            external_id=path.resolve().as_posix(),
            media_type="photo",
            timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
            summary=self._summary,
            latitude=None,
            longitude=None,
            creator_name=None,
            tag_paths=(),
            asset_tag_paths=(),
            persons=(),
            metadata_json={"summary": self._summary},
        )


class _DirectoryBackedConnector(PhotoConnector):
    """Test connector that turns real directory entries into deterministic assets."""

    def extract_metadata_by_path(self, *, paths: list[Path], on_batch_progress=None):
        del on_batch_progress
        return {path.resolve().as_posix(): {} for path in paths}

    def build_asset_candidate(
        self,
        *,
        root: Path,
        path: Path,
        metadata=None,
    ) -> PhotoAssetCandidate:
        del root, metadata
        return PhotoAssetCandidate(
            external_id=path.resolve().as_posix(),
            media_type="photo",
            timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
            summary=path.stem,
            latitude=None,
            longitude=None,
            creator_name=None,
            tag_paths=(),
            asset_tag_paths=(),
            persons=(),
            metadata_json={"name": path.name},
        )


class _HeartbeatConnector(PhotoConnector):
    """Test connector that advances a fake clock during discovery."""

    def __init__(self, *, clock: "_FakeClock") -> None:
        self._clock = clock

    def discover_paths(
        self,
        root: Path,
        *,
        on_path_discovered=None,
    ) -> list[Path]:
        paths = [root / "image-0.jpg", root / "image-1.jpg", root / "image-2.jpg"]
        for index, path in enumerate(paths, start=1):
            if index > 1:
                self._clock.advance(seconds=11)
            if on_path_discovered is not None:
                on_path_discovered(path, index)
        return paths

    def extract_metadata_by_path(self, *, paths: list[Path], on_batch_progress=None):
        del on_batch_progress
        return {path.resolve().as_posix(): {} for path in paths}

    def build_asset_candidate(
        self,
        *,
        root: Path,
        path: Path,
        metadata=None,
    ) -> PhotoAssetCandidate:
        del root, metadata
        return PhotoAssetCandidate(
            external_id=path.resolve().as_posix(),
            media_type="photo",
            timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
            summary=path.name,
            latitude=None,
            longitude=None,
            creator_name=None,
            tag_paths=(),
            asset_tag_paths=(),
            persons=(),
            metadata_json={"path": path.name},
        )


class _MetadataBatchProgressConnector(PhotoConnector):
    """Test connector that emits deterministic metadata batch progress updates."""

    def discover_paths(
        self,
        root: Path,
        *,
        on_path_discovered=None,
    ) -> list[Path]:
        paths = [root / "image-0.jpg", root / "image-1.jpg", root / "image-2.jpg"]
        if on_path_discovered is not None:
            for index, path in enumerate(paths, start=1):
                on_path_discovered(path, index)
        return paths

    def extract_metadata_by_path(self, *, paths: list[Path], on_batch_progress=None):
        if on_batch_progress is not None:
            on_batch_progress(
                PhotoMetadataBatchProgress(
                    event="submitted",
                    batch_index=1,
                    batch_total=2,
                    batch_size=1,
                )
            )
            on_batch_progress(
                PhotoMetadataBatchProgress(
                    event="completed",
                    batch_index=1,
                    batch_total=2,
                    batch_size=1,
                )
            )
            on_batch_progress(
                PhotoMetadataBatchProgress(
                    event="submitted",
                    batch_index=2,
                    batch_total=2,
                    batch_size=2,
                )
            )
            on_batch_progress(
                PhotoMetadataBatchProgress(
                    event="completed",
                    batch_index=2,
                    batch_total=2,
                    batch_size=2,
                )
            )
        return {path.resolve().as_posix(): {} for path in paths}

    def build_asset_candidate(
        self,
        *,
        root: Path,
        path: Path,
        metadata=None,
    ) -> PhotoAssetCandidate:
        del root, metadata
        return PhotoAssetCandidate(
            external_id=path.resolve().as_posix(),
            media_type="photo",
            timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
            summary=path.name,
            latitude=None,
            longitude=None,
            creator_name=None,
            tag_paths=(),
            asset_tag_paths=(),
            persons=(),
            metadata_json={"path": path.name},
        )


class _FakeClock:
    """Simple fake monotonic and wall clock for heartbeat tests."""

    def __init__(self) -> None:
        self._seconds = 0.0

    def advance(self, *, seconds: float) -> None:
        self._seconds += seconds

    def now(self) -> datetime:
        return datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=self._seconds)

    def monotonic(self) -> float:
        return self._seconds


def _create_runtime(*, workspace_root: Path, photos_root: Path):
    database_path = workspace_root / "pixelpast.db"
    media_thumb_root = workspace_root / "thumbs"
    settings = Settings(
        database_url=f"sqlite:///{database_path.as_posix()}",
        photos_root=photos_root,
        media_thumb_root=media_thumb_root,
    )
    runtime = create_runtime_context(settings=settings)
    initialize_database(runtime)
    return runtime


def _create_workspace_dir(*, prefix: str) -> Path:
    workspace_root = Path("var") / f"{prefix}-{uuid4().hex}"
    workspace_root.mkdir(parents=True, exist_ok=False)
    return workspace_root


def _copy_photo_fixtures(*, workspace_root: Path) -> Path:
    photos_root = workspace_root / "photos"
    photos_root.mkdir()
    for fixture_path in sorted((Path("test") / "assets").glob("monalisa-*.jpg")):
        shutil.copy2(fixture_path, photos_root / fixture_path.name)
    return photos_root


def _collect_asset_tag_paths(
    *,
    assets: list[Asset],
    tags: list[Tag],
    asset_tags: list[AssetTag],
) -> dict[str, set[str]]:
    tag_by_id = {tag.id: tag for tag in tags}
    asset_name_by_id = {asset.id: Path(asset.external_id).name for asset in assets}
    collected: dict[str, set[str]] = {name: set() for name in asset_name_by_id.values()}
    for asset_tag in asset_tags:
        asset_name = asset_name_by_id[asset_tag.asset_id]
        tag = tag_by_id[asset_tag.tag_id]
        if tag.path is not None:
            collected[asset_name].add(tag.path)
    return collected


def _collect_asset_person_names(
    *,
    assets: list[Asset],
    people: list[Person],
    asset_people: list[AssetPerson],
) -> dict[str, set[str]]:
    person_by_id = {person.id: person for person in people}
    asset_name_by_id = {asset.id: Path(asset.external_id).name for asset in assets}
    collected: dict[str, set[str]] = {name: set() for name in asset_name_by_id.values()}
    for asset_person in asset_people:
        asset_name = asset_name_by_id[asset_person.asset_id]
        person = person_by_id[asset_person.person_id]
        collected[asset_name].add(person.name)
    return collected
