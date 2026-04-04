"""Integration tests for the album aggregate derive job."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from pixelpast.analytics.album_aggregate import AlbumAggregateJob
from pixelpast.cli.main import app
from pixelpast.persistence.models import (
    Asset,
    AssetCollection,
    AssetCollectionItem,
    AssetCollectionPersonGroup,
    AssetFolder,
    AssetFolderPersonGroup,
    AssetPerson,
    JobRun,
    Person,
    PersonGroup,
    PersonGroupMember,
    Source,
)
from pixelpast.persistence.repositories import AlbumAggregateRepository
from pixelpast.shared.progress import JobProgressSnapshot
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import Settings, get_settings

runner = CliRunner()


def test_album_aggregate_job_materializes_relevance_and_repository_reads() -> None:
    database_path = _build_test_database_path("album-aggregate-job")
    runtime = _create_runtime(database_path=database_path)
    try:
        initialize_database(runtime)
        with runtime.session_factory() as session:
            seeded = _seed_album_aggregate_scenario(session=session)

        result = AlbumAggregateJob().run(runtime=runtime)

        assert result.mode == "full"
        assert result.status == "completed"
        assert result.folder_row_count == 7
        assert result.collection_row_count == 5
        assert result.asset_evidence_count == 4
        assert result.person_group_count == 3

        with runtime.session_factory() as session:
            folder_nodes = list(
                session.execute(select(AssetFolder).order_by(AssetFolder.id)).scalars()
            )
            collection_nodes = list(
                session.execute(
                    select(AssetCollection).order_by(AssetCollection.id)
                ).scalars()
            )
            folder_rows = list(
                session.execute(
                    select(AssetFolderPersonGroup).order_by(
                        AssetFolderPersonGroup.folder_id,
                        AssetFolderPersonGroup.group_id,
                    )
                ).scalars()
            )
            collection_rows = list(
                session.execute(
                    select(AssetCollectionPersonGroup).order_by(
                        AssetCollectionPersonGroup.collection_id,
                        AssetCollectionPersonGroup.group_id,
                    )
                ).scalars()
            )
            repository = AlbumAggregateRepository(session)
            folder_groups = repository.list_person_groups_for_folder(
                folder_id=seeded["folder_ids"]["year"]
            )
            collection_groups = repository.list_person_groups_for_collection(
                collection_id=seeded["collection_ids"]["trips"]
            )
            family_folders = repository.list_folders_for_person_group(
                group_id=seeded["group_ids"]["family"]
            )
            friends_collections = repository.list_collections_for_person_group(
                group_id=seeded["group_ids"]["friends"]
            )

        assert [
            (
                row.folder_id,
                row.group_id,
                row.matched_person_count,
                row.group_person_count,
                row.matched_asset_count,
                row.matched_creator_person_count,
            )
            for row in folder_rows
        ] == [
            (seeded["folder_ids"]["root"], seeded["group_ids"]["family"], 3, 3, 2, 1),
            (seeded["folder_ids"]["root"], seeded["group_ids"]["friends"], 1, 2, 1, 0),
            (seeded["folder_ids"]["year"], seeded["group_ids"]["family"], 3, 3, 2, 1),
            (seeded["folder_ids"]["year"], seeded["group_ids"]["friends"], 1, 2, 1, 0),
            (seeded["folder_ids"]["trip"], seeded["group_ids"]["family"], 2, 3, 1, 1),
            (seeded["folder_ids"]["trip"], seeded["group_ids"]["friends"], 1, 2, 1, 0),
            (seeded["folder_ids"]["home"], seeded["group_ids"]["family"], 1, 3, 1, 0),
        ]
        assert [
            (
                row.collection_id,
                row.group_id,
                row.matched_person_count,
                row.group_person_count,
                row.matched_asset_count,
                row.matched_creator_person_count,
            )
            for row in collection_rows
        ] == [
            (
                seeded["collection_ids"]["portraits"],
                seeded["group_ids"]["family"],
                1,
                3,
                1,
                1,
            ),
            (
                seeded["collection_ids"]["trips"],
                seeded["group_ids"]["family"],
                1,
                3,
                1,
                0,
            ),
            (
                seeded["collection_ids"]["trips"],
                seeded["group_ids"]["friends"],
                2,
                2,
                1,
                1,
            ),
            (
                seeded["collection_ids"]["italy"],
                seeded["group_ids"]["family"],
                1,
                3,
                1,
                0,
            ),
            (
                seeded["collection_ids"]["italy"],
                seeded["group_ids"]["friends"],
                2,
                2,
                1,
                1,
            ),
        ]
        assert [
            (row.group_name, row.matched_person_count, row.matched_asset_count)
            for row in folder_groups
        ] == [
            ("Family", 3, 2),
            ("Friends", 1, 1),
        ]
        assert [
            (
                row.group_name,
                row.matched_person_count,
                row.group_person_count,
                row.matched_creator_person_count,
            )
            for row in collection_groups
        ] == [
            ("Friends", 2, 2, 1),
            ("Family", 1, 3, 0),
        ]
        assert [
            (row.path, row.matched_person_count, row.matched_asset_count)
            for row in family_folders
        ] == [
            ("photos", 3, 2),
            ("photos/2024", 3, 2),
            ("photos/2024/Trip", 2, 1),
            ("photos/2024/Home", 1, 1),
        ]
        assert [
            (
                row.path,
                row.collection_type,
                row.matched_person_count,
                row.matched_creator_person_count,
            )
            for row in friends_collections
        ] == [
            ("Trips", "collection", 2, 1),
            ("Trips/Italy", "collection", 2, 1),
        ]
        assert [(row.path, row.asset_count) for row in folder_nodes] == [
            ("photos", 2),
            ("photos/2024", 2),
            ("photos/2024/Trip", 1),
            ("photos/2024/Home", 1),
        ]
        assert [(row.path, row.asset_count) for row in collection_nodes] == [
            ("Portraits", 1),
            ("Trips", 1),
            ("Trips/Italy", 1),
        ]
    finally:
        runtime.engine.dispose()
        if database_path.exists():
            database_path.unlink()


def test_album_aggregate_job_is_idempotent_and_reflects_group_membership_changes() -> None:
    database_path = _build_test_database_path("album-aggregate-idempotent")
    runtime = _create_runtime(database_path=database_path)
    try:
        initialize_database(runtime)
        with runtime.session_factory() as session:
            seeded = _seed_album_aggregate_scenario(session=session)

        first_result = AlbumAggregateJob().run(runtime=runtime)
        second_result = AlbumAggregateJob().run(runtime=runtime)

        assert first_result.folder_row_count == 7
        assert second_result.folder_row_count == 7

        with runtime.session_factory() as session:
            before_rows = list(
                session.execute(
                    select(AssetCollectionPersonGroup).order_by(
                        AssetCollectionPersonGroup.collection_id,
                        AssetCollectionPersonGroup.group_id,
                    )
                ).scalars()
            )

            session.add(
                PersonGroupMember(
                    group_id=seeded["group_ids"]["family"],
                    person_id=seeded["person_ids"]["dan"],
                )
            )
            session.commit()

        third_result = AlbumAggregateJob().run(runtime=runtime)

        with runtime.session_factory() as session:
            after_rows = list(
                session.execute(
                    select(AssetCollectionPersonGroup).order_by(
                        AssetCollectionPersonGroup.collection_id,
                        AssetCollectionPersonGroup.group_id,
                    )
                ).scalars()
            )

        assert third_result.collection_row_count == 5
        assert [
            (
                row.collection_id,
                row.group_id,
                row.matched_person_count,
                row.group_person_count,
                row.matched_creator_person_count,
            )
            for row in before_rows
        ] == [
            (1, 1, 1, 3, 1),
            (2, 1, 1, 3, 0),
            (2, 2, 2, 2, 1),
            (3, 1, 1, 3, 0),
            (3, 2, 2, 2, 1),
        ]
        assert [
            (
                row.collection_id,
                row.group_id,
                row.matched_person_count,
                row.group_person_count,
                row.matched_creator_person_count,
            )
            for row in after_rows
        ] == [
            (1, 1, 1, 4, 1),
            (2, 1, 2, 4, 1),
            (2, 2, 2, 2, 1),
            (3, 1, 2, 4, 1),
            (3, 2, 2, 2, 1),
        ]
    finally:
        runtime.engine.dispose()
        if database_path.exists():
            database_path.unlink()


def test_album_aggregate_job_persists_derive_run_and_progress() -> None:
    database_path = _build_test_database_path("album-aggregate-progress")
    runtime = _create_runtime(database_path=database_path)
    try:
        initialize_database(runtime)
        with runtime.session_factory() as session:
            _seed_album_aggregate_scenario(session=session)

        snapshots: list[JobProgressSnapshot] = []
        result = AlbumAggregateJob().run(runtime=runtime, progress_callback=snapshots.append)

        with runtime.session_factory() as session:
            job_run = session.execute(select(JobRun).order_by(JobRun.id.desc())).scalar_one()

        assert result.run_id == job_run.id
        assert job_run.type == "derive"
        assert job_run.job == "album-aggregate"
        assert job_run.mode == "full"
        assert job_run.status == "completed"
        assert job_run.phase == "finalization"
        assert job_run.last_heartbeat_at is not None
        assert job_run.progress_json == {
            "total": 1,
            "completed": 1,
            "inserted": 12,
            "updated": 0,
            "unchanged": 0,
            "skipped": 0,
            "failed": 0,
            "missing_from_source": 0,
        }
        assert [
            snapshot.phase
            for snapshot in snapshots
            if snapshot.event == "phase_started"
        ] == [
            "loading album inputs",
            "building album aggregates",
            "persisting album aggregates",
            "finalization",
        ]
        assert snapshots[-1].event == "run_finished"
        assert snapshots[-1].job == "album-aggregate"
        assert snapshots[-1].inserted == 12
    finally:
        runtime.engine.dispose()
        if database_path.exists():
            database_path.unlink()


def test_album_aggregate_job_excludes_group_specific_ignored_persons() -> None:
    database_path = _build_test_database_path("album-aggregate-ignored-persons")
    runtime = _create_runtime(database_path=database_path)
    try:
        initialize_database(runtime)
        with runtime.session_factory() as session:
            seeded = _seed_album_aggregate_scenario(session=session)
            family_group = (
                session.query(PersonGroup)
                .where(PersonGroup.id == seeded["group_ids"]["family"])
                .one()
            )
            family_group.metadata_json = {
                "album_aggregate": {
                    "ignored_person_ids": [
                        seeded["person_ids"]["anna"],
                        seeded["person_ids"]["cara"],
                    ]
                }
            }
            session.commit()

        result = AlbumAggregateJob().run(runtime=runtime)

        assert result.folder_row_count == 6
        assert result.collection_row_count == 4

        with runtime.session_factory() as session:
            family_folder_rows = list(
                session.execute(
                    select(AssetFolderPersonGroup)
                    .where(
                        AssetFolderPersonGroup.group_id == seeded["group_ids"]["family"]
                    )
                    .order_by(AssetFolderPersonGroup.folder_id)
                ).scalars()
            )
            family_collection_rows = list(
                session.execute(
                    select(AssetCollectionPersonGroup)
                    .where(
                        AssetCollectionPersonGroup.group_id
                        == seeded["group_ids"]["family"]
                    )
                    .order_by(AssetCollectionPersonGroup.collection_id)
                ).scalars()
            )

        assert [
            (
                row.folder_id,
                row.matched_person_count,
                row.group_person_count,
                row.matched_asset_count,
                row.matched_creator_person_count,
            )
            for row in family_folder_rows
        ] == [
            (seeded["folder_ids"]["root"], 1, 1, 1, 0),
            (seeded["folder_ids"]["year"], 1, 1, 1, 0),
            (seeded["folder_ids"]["trip"], 1, 1, 1, 0),
        ]
        assert [
            (
                row.collection_id,
                row.matched_person_count,
                row.group_person_count,
                row.matched_asset_count,
                row.matched_creator_person_count,
            )
            for row in family_collection_rows
        ] == [
            (seeded["collection_ids"]["trips"], 1, 1, 1, 0),
            (seeded["collection_ids"]["italy"], 1, 1, 1, 0),
        ]
    finally:
        runtime.engine.dispose()
        if database_path.exists():
            database_path.unlink()


def test_cli_derive_album_aggregate_prints_progress_and_summary(monkeypatch) -> None:
    database_path = _build_test_database_path("cli-album-aggregate")
    monkeypatch.setenv(
        "PIXELPAST_DATABASE_URL",
        f"sqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()

    runtime = create_runtime_context(settings=get_settings())
    try:
        initialize_database(runtime)
        with runtime.session_factory() as session:
            _seed_album_aggregate_scenario(session=session)
    finally:
        runtime.engine.dispose()

    try:
        result = runner.invoke(app, ["derive", "album-aggregate"])

        assert result.exit_code == 0
        assert "[album-aggregate] completed" in result.stdout
        assert "loading album inputs" in result.stdout
        assert "building album aggregates" in result.stdout
        assert "persisting album aggregates" in result.stdout
        assert "inserted: 12" in result.stdout
        assert "failed: 0" in result.stdout
        assert "missing_from_source: 0" in result.stdout

        engine = create_engine(f"sqlite:///{database_path.as_posix()}")
        try:
            with Session(engine) as session:
                job_run = session.execute(select(JobRun).order_by(JobRun.id.desc())).scalar_one()
        finally:
            engine.dispose()

        assert job_run.job == "album-aggregate"
        assert job_run.progress_json is not None
        assert job_run.progress_json["inserted"] == 12
    finally:
        get_settings.cache_clear()
        if database_path.exists():
            database_path.unlink()


def test_album_aggregate_job_batches_large_in_queries_and_persistence(
    monkeypatch,
) -> None:
    database_path = _build_test_database_path("album-aggregate-batching")
    runtime = _create_runtime(database_path=database_path)
    original_batch_size = AlbumAggregateRepository._SQLITE_BATCH_SIZE
    monkeypatch.setattr(AlbumAggregateRepository, "_SQLITE_BATCH_SIZE", 2)
    try:
        initialize_database(runtime)
        with runtime.session_factory() as session:
            _seed_album_aggregate_scenario(session=session)

            extra_people = [
                Person(
                    name=f"Extra Person {index}",
                    aliases=[],
                    path=f"people/extra-{index}",
                    metadata_json=None,
                )
                for index in range(6)
            ]
            session.add_all(extra_people)
            session.flush()

            extra_group = PersonGroup(
                name="Big Group",
                type="manual",
                path="groups/big",
                metadata_json={},
            )
            session.add(extra_group)
            session.flush()
            session.add_all(
                [
                    PersonGroupMember(group_id=extra_group.id, person_id=person.id)
                    for person in extra_people
                ]
            )

            root_folder = session.execute(
                select(AssetFolder).where(AssetFolder.path == "photos/2024/Trip")
            ).scalar_one()
            photos_source = session.execute(
                select(Source).where(Source.type == "photos")
            ).scalar_one()

            extra_assets = [
                Asset(
                    short_id=f"BATCH{index:03d}",
                    source_id=photos_source.id,
                    external_id=f"/photos/2024/Trip/batch-{index}.jpg",
                    media_type="photo",
                    timestamp=_timestamp(2024, 7, 10 + index, 10),
                    folder_id=root_folder.id,
                    creator_person_id=None,
                    metadata_json={"filename": f"batch-{index}.jpg"},
                )
                for index in range(6)
            ]
            session.add_all(extra_assets)
            session.flush()
            session.add_all(
                [
                    AssetPerson(asset_id=asset.id, person_id=person.id)
                    for asset, person in zip(extra_assets, extra_people, strict=True)
                ]
            )
            session.commit()

        result = AlbumAggregateJob().run(runtime=runtime)

        assert result.status == "completed"
        assert result.asset_evidence_count == 10
        assert result.person_group_count == 4
        assert result.folder_row_count >= 8
        assert result.collection_row_count >= 5
    finally:
        monkeypatch.setattr(
            AlbumAggregateRepository,
            "_SQLITE_BATCH_SIZE",
            original_batch_size,
        )
        runtime.engine.dispose()
        if database_path.exists():
            database_path.unlink()


def _seed_album_aggregate_scenario(*, session: Session) -> dict[str, dict[str, int]]:
    photos_source = Source(
        name="Photos",
        type="photos",
        external_id="photos:test",
        config={},
    )
    lightroom_source = Source(
        name="Lightroom",
        type="lightroom_catalog",
        external_id="lightroom:test",
        config={},
    )
    session.add_all([photos_source, lightroom_source])
    session.flush()

    anna = Person(name="Anna", aliases=[], path="people/anna", metadata_json=None)
    ben = Person(name="Ben", aliases=[], path="people/ben", metadata_json=None)
    cara = Person(name="Cara", aliases=[], path="people/cara", metadata_json=None)
    dan = Person(name="Dan", aliases=[], path="people/dan", metadata_json=None)
    session.add_all([anna, ben, cara, dan])
    session.flush()

    family = PersonGroup(name="Family", type="manual", path="groups/family", metadata_json={})
    friends = PersonGroup(name="Friends", type="manual", path="groups/friends", metadata_json={})
    empty = PersonGroup(name="Empty", type="manual", path="groups/empty", metadata_json={})
    session.add_all([family, friends, empty])
    session.flush()
    session.add_all(
        [
            PersonGroupMember(group_id=family.id, person_id=anna.id),
            PersonGroupMember(group_id=family.id, person_id=ben.id),
            PersonGroupMember(group_id=family.id, person_id=cara.id),
            PersonGroupMember(group_id=friends.id, person_id=ben.id),
            PersonGroupMember(group_id=friends.id, person_id=dan.id),
        ]
    )

    folder_root = AssetFolder(
        source_id=photos_source.id,
        parent_id=None,
        name="photos",
        path="photos",
    )
    folder_year = AssetFolder(
        source_id=photos_source.id,
        parent_id=None,
        name="2024",
        path="photos/2024",
    )
    session.add_all([folder_root, folder_year])
    session.flush()
    folder_year.parent_id = folder_root.id
    folder_trip = AssetFolder(
        source_id=photos_source.id,
        parent_id=folder_year.id,
        name="Trip",
        path="photos/2024/Trip",
    )
    folder_home = AssetFolder(
        source_id=photos_source.id,
        parent_id=folder_year.id,
        name="Home",
        path="photos/2024/Home",
    )
    session.add_all([folder_trip, folder_home])
    session.flush()

    collection_portraits = AssetCollection(
        source_id=lightroom_source.id,
        parent_id=None,
        name="Portraits",
        path="Portraits",
        external_id="portraits",
        collection_type="collection",
        metadata_json=None,
    )
    collection_trips = AssetCollection(
        source_id=lightroom_source.id,
        parent_id=None,
        name="Trips",
        path="Trips",
        external_id="trips",
        collection_type="collection",
        metadata_json=None,
    )
    session.add_all([collection_portraits, collection_trips])
    session.flush()
    collection_italy = AssetCollection(
        source_id=lightroom_source.id,
        parent_id=collection_trips.id,
        name="Italy",
        path="Trips/Italy",
        external_id="trips:italy",
        collection_type="collection",
        metadata_json=None,
    )
    session.add(collection_italy)
    session.flush()

    trip_asset = Asset(
        short_id="TRIP0001",
        source_id=photos_source.id,
        external_id="/photos/2024/Trip/trip-1.jpg",
        media_type="photo",
        timestamp=_timestamp(2024, 7, 5, 10),
        folder_id=folder_trip.id,
        creator_person_id=anna.id,
        metadata_json={"filename": "trip-1.jpg"},
    )
    home_asset = Asset(
        short_id="HOME0001",
        source_id=photos_source.id,
        external_id="/photos/2024/Home/home-1.jpg",
        media_type="photo",
        timestamp=_timestamp(2024, 7, 6, 11),
        folder_id=folder_home.id,
        creator_person_id=None,
        metadata_json={"filename": "home-1.jpg"},
    )
    italy_asset = Asset(
        short_id="ITAL0001",
        source_id=lightroom_source.id,
        external_id="lr:italy-1",
        media_type="photo",
        timestamp=_timestamp(2024, 8, 1, 9),
        folder_id=None,
        creator_person_id=dan.id,
        metadata_json={"file_name": "italy-1.jpg"},
    )
    portrait_asset = Asset(
        short_id="PORT0001",
        source_id=lightroom_source.id,
        external_id="lr:portrait-1",
        media_type="photo",
        timestamp=_timestamp(2024, 8, 2, 9),
        folder_id=None,
        creator_person_id=anna.id,
        metadata_json={"file_name": "portrait-1.jpg"},
    )
    session.add_all([trip_asset, home_asset, italy_asset, portrait_asset])
    session.flush()

    session.add_all(
        [
            AssetPerson(asset_id=trip_asset.id, person_id=anna.id),
            AssetPerson(asset_id=trip_asset.id, person_id=ben.id),
            AssetPerson(asset_id=home_asset.id, person_id=cara.id),
            AssetPerson(asset_id=italy_asset.id, person_id=ben.id),
        ]
    )
    session.add_all(
        [
            AssetCollectionItem(
                collection_id=collection_trips.id,
                asset_id=italy_asset.id,
            ),
            AssetCollectionItem(
                collection_id=collection_italy.id,
                asset_id=italy_asset.id,
            ),
            AssetCollectionItem(
                collection_id=collection_portraits.id,
                asset_id=portrait_asset.id,
            ),
        ]
    )
    session.commit()

    return {
        "person_ids": {
            "anna": anna.id,
            "ben": ben.id,
            "cara": cara.id,
            "dan": dan.id,
        },
        "group_ids": {
            "family": family.id,
            "friends": friends.id,
            "empty": empty.id,
        },
        "folder_ids": {
            "root": folder_root.id,
            "year": folder_year.id,
            "trip": folder_trip.id,
            "home": folder_home.id,
        },
        "collection_ids": {
            "portraits": collection_portraits.id,
            "trips": collection_trips.id,
            "italy": collection_italy.id,
        },
    }


def _create_runtime(*, database_path: Path):
    return create_runtime_context(
        settings=Settings(database_url=f"sqlite:///{database_path.as_posix()}")
    )


def _timestamp(year: int, month: int, day: int, hour: int) -> datetime:
    return datetime(year, month, day, hour, 0, 0, tzinfo=UTC)


def _build_test_database_path(prefix: str) -> Path:
    database_dir = Path("var")
    database_dir.mkdir(exist_ok=True)
    return database_dir / f"{prefix}-{uuid4().hex}.db"
