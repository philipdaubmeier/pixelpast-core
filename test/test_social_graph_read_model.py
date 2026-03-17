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
                {"person_ids": [1, 2], "weight": 2},
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
                {"person_ids": [1, 2], "weight": 2},
                {"person_ids": [1, 3], "weight": 1},
                {"person_ids": [2, 3], "weight": 1},
            ],
        }
    finally:
        runtime.engine.dispose()


def _create_runtime():
    settings = Settings(database_url="sqlite:///:memory:")
    runtime = create_runtime_context(settings=settings)
    initialize_database(runtime)
    return runtime
