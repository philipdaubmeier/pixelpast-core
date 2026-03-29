"""Integration tests for manage-data catalog contracts and persistence."""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from pixelpast.api.app import create_app
from pixelpast.persistence.models import Person, PersonGroup, PersonGroupMember
from pixelpast.persistence.repositories import MANUAL_PERSON_GROUP_TYPE
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import Settings


def test_manage_data_persons_endpoint_lists_catalog_in_stable_shape() -> None:
    workspace_root = _create_workspace_dir(prefix="manage-data-persons-list")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        with runtime.session_factory() as session:
            session.add_all(
                [
                    Person(
                        name="Milo Tan",
                        aliases=["Milo", "Miles"],
                        path=None,
                        metadata_json=None,
                    ),
                    Person(
                        name="Anna Becker",
                        aliases=[" Annie ", "", "Annie"],
                        path="family/anna-becker",
                        metadata_json=None,
                    ),
                ]
            )
            session.commit()

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.get("/api/manage-data/persons")

        assert response.status_code == 200
        assert response.json() == {
            "persons": [
                {
                    "id": 2,
                    "name": "Anna Becker",
                    "aliases": ["Annie"],
                    "path": "family/anna-becker",
                },
                {
                    "id": 1,
                    "name": "Milo Tan",
                    "aliases": ["Milo", "Miles"],
                    "path": None,
                },
            ]
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_manage_data_persons_save_supports_create_and_update_only() -> None:
    workspace_root = _create_workspace_dir(prefix="manage-data-persons-save")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        with runtime.session_factory() as session:
            session.add(
                Person(
                    name="Anna Becker",
                    aliases=["Anna"],
                    path="family/anna-becker",
                    metadata_json=None,
                )
            )
            session.commit()

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.put(
                "/api/manage-data/persons",
                json={
                    "persons": [
                        {
                            "id": 1,
                            "name": "Anna Becker",
                            "aliases": ["Anna", " Annie ", ""],
                            "path": "family/anna-becker",
                        },
                        {
                            "name": "Milo Tan",
                            "aliases": ["Miles", "Miles", " Milo "],
                            "path": "friends/milo-tan",
                        },
                    ],
                    "delete_ids": [],
                },
            )

        assert response.status_code == 200
        assert response.json() == {
            "persons": [
                {
                    "id": 1,
                    "name": "Anna Becker",
                    "aliases": ["Anna", "Annie"],
                    "path": "family/anna-becker",
                },
                {
                    "id": 2,
                    "name": "Milo Tan",
                    "aliases": ["Miles", "Milo"],
                    "path": "friends/milo-tan",
                },
            ]
        }

        with runtime.session_factory() as session:
            people = session.query(Person).order_by(Person.id).all()

        assert [person.aliases for person in people] == [
            ["Anna", "Annie"],
            ["Miles", "Milo"],
        ]

        with TestClient(app) as client:
            rejected_response = client.put(
                "/api/manage-data/persons",
                json={"persons": [], "delete_ids": [1]},
            )

        assert rejected_response.status_code == 400
        assert rejected_response.json() == {
            "detail": "person deletion is not supported in the v1 manage-data contract"
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_manage_data_persons_save_rejects_duplicate_paths() -> None:
    workspace_root = _create_workspace_dir(prefix="manage-data-persons-unique-path")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        with runtime.session_factory() as session:
            session.add_all(
                [
                    Person(
                        name="Anna Becker",
                        aliases=[],
                        path="family/anna-becker",
                        metadata_json=None,
                    ),
                    Person(
                        name="Milo Tan",
                        aliases=[],
                        path=None,
                        metadata_json=None,
                    ),
                ]
            )
            session.commit()

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            response = client.put(
                "/api/manage-data/persons",
                json={
                    "persons": [
                        {
                            "id": 1,
                            "name": "Anna Becker",
                            "aliases": [],
                            "path": "family/anna-becker",
                        },
                        {
                            "id": 2,
                            "name": "Milo Tan",
                            "aliases": [],
                            "path": "family/anna-becker",
                        },
                    ],
                    "delete_ids": [],
                },
            )

        assert response.status_code == 400
        assert response.json() == {
            "detail": "person path 'family/anna-becker' must be unique"
        }
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_manage_data_person_groups_save_supports_member_counts_and_cleanup() -> None:
    workspace_root = _create_workspace_dir(prefix="manage-data-person-groups-save")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        with runtime.session_factory() as session:
            first_person = Person(
                name="Anna Becker",
                aliases=[],
                path="family/anna-becker",
                metadata_json=None,
            )
            second_person = Person(
                name="Milo Tan",
                aliases=[],
                path="friends/milo-tan",
                metadata_json=None,
            )
            keep_group = PersonGroup(
                name="Immediate Family",
                type="legacy",
                path="legacy/family",
                metadata_json={"seeded": True},
            )
            delete_group = PersonGroup(
                name="Berlin Friends",
                type="legacy",
                path="legacy/friends",
                metadata_json={"seeded": True},
            )
            session.add_all([first_person, second_person, keep_group, delete_group])
            session.flush()
            session.add_all(
                [
                    PersonGroupMember(group_id=keep_group.id, person_id=first_person.id),
                    PersonGroupMember(group_id=keep_group.id, person_id=second_person.id),
                    PersonGroupMember(group_id=delete_group.id, person_id=second_person.id),
                ]
            )
            session.commit()

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            list_response = client.get("/api/manage-data/person-groups")

        assert list_response.status_code == 200
        assert list_response.json() == {
            "person_groups": [
                {"id": 2, "name": "Berlin Friends", "member_count": 1},
                {"id": 1, "name": "Immediate Family", "member_count": 2},
            ]
        }

        with TestClient(app) as client:
            save_response = client.put(
                "/api/manage-data/person-groups",
                json={
                    "person_groups": [
                        {"id": 1, "name": "Immediate Family Core"},
                        {"name": "Travel Buddies"},
                    ],
                    "delete_ids": [2],
                },
            )

        assert save_response.status_code == 200
        assert save_response.json() == {
            "person_groups": [
                {"id": 1, "name": "Immediate Family Core", "member_count": 2},
                {"id": 2, "name": "Travel Buddies", "member_count": 0},
            ]
        }

        with runtime.session_factory() as session:
            stored_groups = session.query(PersonGroup).order_by(PersonGroup.id).all()
            stored_memberships = (
                session.query(PersonGroupMember)
                .order_by(PersonGroupMember.group_id, PersonGroupMember.person_id)
                .all()
            )

        assert [(group.id, group.name, group.type) for group in stored_groups] == [
            (1, "Immediate Family Core", MANUAL_PERSON_GROUP_TYPE),
            (2, "Travel Buddies", MANUAL_PERSON_GROUP_TYPE),
        ]
        assert [(link.group_id, link.person_id) for link in stored_memberships] == [
            (1, 1),
            (1, 2),
        ]
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_manage_data_person_group_membership_contract_replaces_member_set() -> None:
    workspace_root = _create_workspace_dir(prefix="manage-data-person-group-membership")
    runtime = None
    try:
        runtime = _create_runtime(workspace_root=workspace_root)
        with runtime.session_factory() as session:
            anna = Person(
                name="Anna Becker",
                aliases=["Annie"],
                path="family/anna-becker",
                metadata_json=None,
            )
            milo = Person(
                name="Milo Tan",
                aliases=[],
                path="friends/milo-tan",
                metadata_json=None,
            )
            noa = Person(
                name="Noa Stein",
                aliases=["N."],
                path="friends/noa-stein",
                metadata_json=None,
            )
            group = PersonGroup(
                name="Travel Buddies",
                type=MANUAL_PERSON_GROUP_TYPE,
                path=None,
                metadata_json={},
            )
            session.add_all([anna, milo, noa, group])
            session.flush()
            session.add_all(
                [
                    PersonGroupMember(group_id=group.id, person_id=anna.id),
                    PersonGroupMember(group_id=group.id, person_id=milo.id),
                ]
            )
            session.commit()

        app = create_app(settings=runtime.settings)
        with TestClient(app) as client:
            get_response = client.get("/api/manage-data/person-groups/1/members")

        assert get_response.status_code == 200
        assert get_response.json() == {
            "person_group": {
                "id": 1,
                "name": "Travel Buddies",
                "member_count": 2,
            },
            "members": [
                {
                    "id": 1,
                    "name": "Anna Becker",
                    "aliases": ["Annie"],
                    "path": "family/anna-becker",
                },
                {
                    "id": 2,
                    "name": "Milo Tan",
                    "aliases": [],
                    "path": "friends/milo-tan",
                },
            ],
        }

        with TestClient(app) as client:
            save_response = client.put(
                "/api/manage-data/person-groups/1/members",
                json={"person_ids": [3, 3, 1]},
            )

        assert save_response.status_code == 200
        assert save_response.json() == {
            "person_group": {
                "id": 1,
                "name": "Travel Buddies",
                "member_count": 2,
            },
            "members": [
                {
                    "id": 1,
                    "name": "Anna Becker",
                    "aliases": ["Annie"],
                    "path": "family/anna-becker",
                },
                {
                    "id": 3,
                    "name": "Noa Stein",
                    "aliases": ["N."],
                    "path": "friends/noa-stein",
                },
            ],
        }

        with runtime.session_factory() as session:
            memberships = (
                session.query(PersonGroupMember)
                .order_by(PersonGroupMember.group_id, PersonGroupMember.person_id)
                .all()
            )

        assert [(link.group_id, link.person_id) for link in memberships] == [
            (1, 1),
            (1, 3),
        ]

        with TestClient(app) as client:
            rejected_response = client.put(
                "/api/manage-data/person-groups/1/members",
                json={"person_ids": [999]},
            )

        assert rejected_response.status_code == 400
        assert rejected_response.json() == {"detail": "person id 999 does not exist"}
    finally:
        if runtime is not None:
            runtime.engine.dispose()
        shutil.rmtree(workspace_root, ignore_errors=True)


def _create_runtime(*, workspace_root: Path):
    database_path = workspace_root / "pixelpast.db"
    settings = Settings(database_url=f"sqlite:///{database_path.as_posix()}")
    runtime = create_runtime_context(settings=settings)
    initialize_database(runtime)
    return runtime


def _create_workspace_dir(*, prefix: str) -> Path:
    workspace_root = Path("var") / f"{prefix}-{uuid4().hex}"
    workspace_root.mkdir(parents=True, exist_ok=False)
    return workspace_root
