"""Integration tests for Lightroom catalog persistence and lifecycle seams."""

from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from pixelpast.ingestion.lightroom_catalog import (
    LightroomCatalogConnector,
    LightroomCatalogDescriptor,
    LightroomCatalogIngestionPersistenceScope,
    LightroomCatalogIngestionRunCoordinator,
    LightroomCatalogTransformer,
    build_lightroom_catalog_source_external_id,
)
from pixelpast.persistence.models import (
    Asset,
    AssetPerson,
    AssetTag,
    JobRun,
    Person,
    Source,
    Tag,
)
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import Settings

_FIXTURE_PATH = Path("test/assets/lightroom-classic-catalog-test-fixture.lrcat").resolve()


def test_lightroom_catalog_persistence_scope_persists_assets_and_is_idempotent() -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    try:
        catalog_path = workspace_root / _FIXTURE_PATH.name
        shutil.copy2(_FIXTURE_PATH, catalog_path)
        descriptor = LightroomCatalogDescriptor(path=catalog_path)

        first_candidate = _build_catalog_candidate(descriptor=descriptor)
        lifecycle = LightroomCatalogIngestionRunCoordinator()
        first_run_id = lifecycle.create_run(
            runtime=runtime,
            resolved_root=catalog_path.resolve(),
        )
        first_scope = LightroomCatalogIngestionPersistenceScope(
            runtime=runtime,
            lifecycle=lifecycle,
            resolved_root=catalog_path.resolve(),
        )
        first_missing = first_scope.count_missing_from_source(
            resolved_root=catalog_path.resolve(),
            discovered_units=(descriptor,),
            candidates=(first_candidate,),
        )
        first_outcome = first_scope.persist(candidate=first_candidate)
        first_scope.commit()
        first_scope.close()

        second_candidate = _build_catalog_candidate(descriptor=descriptor)
        second_run_id = lifecycle.create_run(
            runtime=runtime,
            resolved_root=catalog_path.resolve(),
        )
        second_scope = LightroomCatalogIngestionPersistenceScope(
            runtime=runtime,
            lifecycle=lifecycle,
            resolved_root=catalog_path.resolve(),
        )
        second_outcome = second_scope.persist(candidate=second_candidate)
        second_scope.commit()
        second_scope.close()

        renamed_asset = replace(
            second_candidate.assets[1],
            metadata_json={
                **(second_candidate.assets[1].metadata_json or {}),
                "file_name": "renamed-monalisa-2.jpg",
                "file_path": "C:/renamed/renamed-monalisa-2.jpg",
            },
        )
        renamed_candidate = replace(
            second_candidate,
            assets=(
                second_candidate.assets[0],
                renamed_asset,
                second_candidate.assets[2],
            ),
        )
        third_run_id = lifecycle.create_run(
            runtime=runtime,
            resolved_root=catalog_path.resolve(),
        )
        third_scope = LightroomCatalogIngestionPersistenceScope(
            runtime=runtime,
            lifecycle=lifecycle,
            resolved_root=catalog_path.resolve(),
        )
        third_outcome = third_scope.persist(candidate=renamed_candidate)
        third_scope.commit()
        third_scope.close()

        with runtime.session_factory() as session:
            assets = list(session.execute(select(Asset).order_by(Asset.external_id)).scalars())
            people = list(session.execute(select(Person).order_by(Person.name)).scalars())
            tags = list(session.execute(select(Tag).order_by(Tag.path)).scalars())
            asset_tags = list(session.execute(select(AssetTag)).scalars())
            asset_people = list(session.execute(select(AssetPerson)).scalars())
            sources = list(session.execute(select(Source).order_by(Source.id)).scalars())
            job_runs = list(session.execute(select(JobRun).order_by(JobRun.id)).scalars())

        asset_by_external_id = {asset.external_id: asset for asset in assets}
        renamed_external_id = second_candidate.assets[1].external_id

        assert first_run_id == 1
        assert second_run_id == 2
        assert third_run_id == 3
        assert first_missing == 0
        assert first_outcome == (
            "inserted=3;updated=0;unchanged=0;missing_from_source=0;"
            "skipped=0;persisted_asset_count=3"
        )
        assert second_outcome == (
            "inserted=0;updated=0;unchanged=3;missing_from_source=0;"
            "skipped=0;persisted_asset_count=3"
        )
        assert third_outcome == (
            "inserted=0;updated=1;unchanged=2;missing_from_source=0;"
            "skipped=0;persisted_asset_count=3"
        )

        assert len(assets) == 3
        assert len(people) == 3
        assert len(tags) == 10
        assert len(asset_tags) == 17
        assert len(asset_people) == 5
        assert len(sources) == 1
        assert len(job_runs) == 3

        assert sources[0].type == "lightroom_catalog"
        assert sources[0].external_id == build_lightroom_catalog_source_external_id(
            catalog_path=catalog_path.resolve()
        )
        assert sources[0].config == {"catalog_path": catalog_path.resolve().as_posix()}
        assert [job_run.job for job_run in job_runs] == ["lightroom_catalog"] * 3

        renamed_asset_model = asset_by_external_id[renamed_external_id]
        assert renamed_asset_model.summary == "Title 2"
        assert renamed_asset_model.metadata_json == {
            "file_name": "renamed-monalisa-2.jpg",
            "file_path": "C:/renamed/renamed-monalisa-2.jpg",
            "preserved_file_name": "monalisa-2.jpg",
            "caption": None,
            "camera": None,
            "lens": None,
            "aperture_f_number": None,
            "shutter_speed_seconds": None,
            "iso": None,
            "rating": 4,
            "color_label": "Gelb",
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
        assert {person.name for person in people} == {
            "John Doe",
            "Leonardo da Vinci",
            "Mona Lisa",
        }
    finally:
        runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_lightroom_catalog_run_coordinator_persists_source_and_initial_job_run() -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    try:
        catalog_path = workspace_root / _FIXTURE_PATH.name
        shutil.copy2(_FIXTURE_PATH, catalog_path)

        run_id = LightroomCatalogIngestionRunCoordinator().create_run(
            runtime=runtime,
            resolved_root=catalog_path.resolve(),
        )

        with runtime.session_factory() as session:
            source = session.execute(select(Source)).scalar_one()
            job_run = session.execute(
                select(JobRun).where(JobRun.id == run_id)
            ).scalar_one()

        assert source.type == "lightroom_catalog"
        assert source.external_id == build_lightroom_catalog_source_external_id(
            catalog_path=catalog_path.resolve()
        )
        assert source.config == {"catalog_path": catalog_path.resolve().as_posix()}
        assert job_run.type == "ingest"
        assert job_run.job == "lightroom_catalog"
        assert job_run.mode == "full"
        assert job_run.phase == "initializing"
        assert job_run.status == "running"
        assert job_run.progress_json == {
            "total": None,
            "completed": 0,
            "inserted": 0,
            "updated": 0,
            "unchanged": 0,
            "skipped": 0,
            "failed": 0,
            "missing_from_source": 0,
            "root_path": catalog_path.resolve().as_posix(),
        }
    finally:
        runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def _build_catalog_candidate(*, descriptor: LightroomCatalogDescriptor):
    connector = LightroomCatalogConnector()
    loaded_catalog = connector.fetch_catalogs(catalogs=(descriptor,))[0]
    return LightroomCatalogTransformer().build_catalog_candidate(loaded_catalog)


def _create_runtime():
    runtime = create_runtime_context(settings=Settings(database_url="sqlite://"))
    initialize_database(runtime)
    return runtime


def _create_workspace_root() -> Path:
    workspace_root = Path("var") / f"lightroom-catalog-{uuid4().hex}"
    workspace_root.mkdir(parents=True, exist_ok=False)
    return workspace_root
