"""Tests for canonical social-graph read modeling and projection."""

from __future__ import annotations

from datetime import UTC, datetime

from pixelpast.api.providers.social_graph import build_social_graph_response
from pixelpast.persistence.models import Asset, AssetPerson, Person
from pixelpast.persistence.repositories import SocialGraphReadRepository
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import Settings


def test_social_graph_projection_keeps_isolated_qualifying_person_without_links() -> None:
    runtime = _create_runtime()
    try:
        with runtime.session_factory() as session:
            anna = Person(name="Anna", aliases=None, metadata_json=None)
            session.add(anna)
            session.flush()
            asset = Asset(
                external_id="asset-1",
                media_type="photo",
                timestamp=datetime(2024, 1, 2, 9, 0, tzinfo=UTC),
                summary=None,
                latitude=None,
                longitude=None,
                creator_person_id=None,
                metadata_json={},
            )
            session.add(asset)
            session.flush()
            session.add(AssetPerson(asset_id=asset.id, person_id=anna.id))
            session.commit()

            response = build_social_graph_response(
                SocialGraphReadRepository(session).read_projection()
            )

        assert response.model_dump() == {
            "persons": [
                {
                    "id": 1,
                    "name": "Anna",
                    "occurrence_count": 1,
                }
            ],
            "links": [],
        }
    finally:
        runtime.engine.dispose()


def test_social_graph_projection_counts_repeated_pair_co_occurrence_across_assets() -> None:
    runtime = _create_runtime()
    try:
        with runtime.session_factory() as session:
            anna = Person(name="Anna", aliases=None, metadata_json=None)
            ben = Person(name="Ben", aliases=None, metadata_json=None)
            session.add_all([anna, ben])
            session.flush()

            first_asset = Asset(
                external_id="asset-1",
                media_type="photo",
                timestamp=datetime(2024, 1, 2, 9, 0, tzinfo=UTC),
                summary=None,
                latitude=None,
                longitude=None,
                creator_person_id=None,
                metadata_json={},
            )
            second_asset = Asset(
                external_id="asset-2",
                media_type="photo",
                timestamp=datetime(2024, 1, 2, 10, 0, tzinfo=UTC),
                summary=None,
                latitude=None,
                longitude=None,
                creator_person_id=None,
                metadata_json={},
            )
            session.add_all([first_asset, second_asset])
            session.flush()
            session.add_all(
                [
                    AssetPerson(asset_id=first_asset.id, person_id=anna.id),
                    AssetPerson(asset_id=first_asset.id, person_id=ben.id),
                    AssetPerson(asset_id=second_asset.id, person_id=anna.id),
                    AssetPerson(asset_id=second_asset.id, person_id=ben.id),
                ]
            )
            session.commit()

            snapshot = SocialGraphReadRepository(session).read_projection()
            response = build_social_graph_response(snapshot)

        assert response.model_dump() == {
            "persons": [
                {"id": 1, "name": "Anna", "occurrence_count": 2},
                {"id": 2, "name": "Ben", "occurrence_count": 2},
            ],
            "links": [
                {"person_ids": [1, 2], "weight": 2, "affinity": 0.5},
            ],
        }
    finally:
        runtime.engine.dispose()


def test_social_graph_projection_orders_pairs_stably_and_treats_links_as_unordered() -> None:
    runtime = _create_runtime()
    try:
        with runtime.session_factory() as session:
            zoe = Person(name="Zoe", aliases=None, metadata_json=None)
            anna = Person(name="Anna", aliases=None, metadata_json=None)
            ben = Person(name="Ben", aliases=None, metadata_json=None)
            session.add_all([zoe, anna, ben])
            session.flush()

            first_asset = Asset(
                external_id="asset-1",
                media_type="photo",
                timestamp=datetime(2024, 1, 2, 9, 0, tzinfo=UTC),
                summary=None,
                latitude=None,
                longitude=None,
                creator_person_id=None,
                metadata_json={},
            )
            second_asset = Asset(
                external_id="asset-2",
                media_type="photo",
                timestamp=datetime(2024, 1, 3, 9, 0, tzinfo=UTC),
                summary=None,
                latitude=None,
                longitude=None,
                creator_person_id=None,
                metadata_json={},
            )
            session.add_all([first_asset, second_asset])
            session.flush()
            session.add_all(
                [
                    AssetPerson(asset_id=first_asset.id, person_id=zoe.id),
                    AssetPerson(asset_id=first_asset.id, person_id=anna.id),
                    AssetPerson(asset_id=second_asset.id, person_id=ben.id),
                    AssetPerson(asset_id=second_asset.id, person_id=anna.id),
                    AssetPerson(asset_id=second_asset.id, person_id=zoe.id),
                ]
            )
            session.commit()

            response = build_social_graph_response(
                SocialGraphReadRepository(session).read_projection()
            )

        assert response.model_dump() == {
            "persons": [
                {"id": 2, "name": "Anna", "occurrence_count": 2},
                {"id": 3, "name": "Ben", "occurrence_count": 1},
                {"id": 1, "name": "Zoe", "occurrence_count": 2},
            ],
            "links": [
                {"person_ids": [1, 2], "weight": 2, "affinity": 0.5},
                {"person_ids": [1, 3], "weight": 1, "affinity": 0.235702},
                {"person_ids": [2, 3], "weight": 1, "affinity": 0.235702},
            ],
        }
    finally:
        runtime.engine.dispose()


def test_social_graph_affinity_penalizes_hub_overlap_against_exclusive_pair() -> None:
    runtime = _create_runtime()
    try:
        with runtime.session_factory() as session:
            hub = Person(name="Hub", aliases=None, metadata_json=None)
            worker_left = Person(name="Worker Left", aliases=None, metadata_json=None)
            worker_right = Person(name="Worker Right", aliases=None, metadata_json=None)
            outsider = Person(name="Outsider", aliases=None, metadata_json=None)
            session.add_all([hub, worker_left, worker_right, outsider])
            session.flush()

            assets = [
                Asset(
                    external_id=f"asset-{index}",
                    media_type="photo",
                    timestamp=datetime(2024, 1, index + 1, 9, 0, tzinfo=UTC),
                    summary=None,
                    latitude=None,
                    longitude=None,
                    creator_person_id=None,
                    metadata_json={},
                )
                for index in range(4)
            ]
            session.add_all(assets)
            session.flush()
            session.add_all(
                [
                    AssetPerson(asset_id=assets[0].id, person_id=hub.id),
                    AssetPerson(asset_id=assets[0].id, person_id=worker_left.id),
                    AssetPerson(asset_id=assets[0].id, person_id=worker_right.id),
                    AssetPerson(asset_id=assets[1].id, person_id=hub.id),
                    AssetPerson(asset_id=assets[1].id, person_id=worker_left.id),
                    AssetPerson(asset_id=assets[1].id, person_id=worker_right.id),
                    AssetPerson(asset_id=assets[2].id, person_id=hub.id),
                    AssetPerson(asset_id=assets[2].id, person_id=outsider.id),
                    AssetPerson(asset_id=assets[3].id, person_id=hub.id),
                    AssetPerson(asset_id=assets[3].id, person_id=outsider.id),
                ]
            )
            session.commit()

            response = build_social_graph_response(
                SocialGraphReadRepository(session).read_projection()
            )

        link_by_person_ids = {
            tuple(link["person_ids"]): link
            for link in response.model_dump()["links"]
        }
        assert link_by_person_ids[(2, 3)]["weight"] == 2
        assert link_by_person_ids[(1, 2)]["weight"] == 2
        assert link_by_person_ids[(1, 2)]["affinity"] < link_by_person_ids[(2, 3)]["affinity"]
        assert link_by_person_ids[(1, 3)]["affinity"] < link_by_person_ids[(2, 3)]["affinity"]
    finally:
        runtime.engine.dispose()


def test_social_graph_projection_excludes_assets_above_people_cutoff() -> None:
    runtime = _create_runtime()
    try:
        with runtime.session_factory() as session:
            people = [
                Person(name=f"Person {index}", aliases=None, metadata_json=None)
                for index in range(1, 12)
            ]
            session.add_all(people)
            session.flush()

            small_asset = Asset(
                external_id="asset-small",
                media_type="photo",
                timestamp=datetime(2024, 1, 2, 9, 0, tzinfo=UTC),
                summary=None,
                latitude=None,
                longitude=None,
                creator_person_id=None,
                metadata_json={},
            )
            large_asset = Asset(
                external_id="asset-large",
                media_type="photo",
                timestamp=datetime(2024, 1, 3, 9, 0, tzinfo=UTC),
                summary=None,
                latitude=None,
                longitude=None,
                creator_person_id=None,
                metadata_json={},
            )
            session.add_all([small_asset, large_asset])
            session.flush()

            session.add_all(
                [
                    AssetPerson(asset_id=small_asset.id, person_id=people[0].id),
                    AssetPerson(asset_id=small_asset.id, person_id=people[1].id),
                ]
                + [
                    AssetPerson(asset_id=large_asset.id, person_id=person.id)
                    for person in people
                ]
            )
            session.commit()

            response = build_social_graph_response(
                SocialGraphReadRepository(session).read_projection(
                    max_people_per_asset=10,
                )
            )

        assert response.model_dump() == {
            "persons": [
                {"id": 1, "name": "Person 1", "occurrence_count": 1},
                {"id": 2, "name": "Person 2", "occurrence_count": 1},
            ],
            "links": [
                {"person_ids": [1, 2], "weight": 1, "affinity": 0.333333},
            ],
        }
    finally:
        runtime.engine.dispose()


def _create_runtime():
    settings = Settings(database_url="sqlite:///:memory:")
    runtime = create_runtime_context(settings=settings)
    initialize_database(runtime)
    return runtime
