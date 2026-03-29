"""Repositories for manual manage-data catalog reads and writes."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from pixelpast.persistence.models import Person, PersonGroup, PersonGroupMember

MANUAL_PERSON_GROUP_TYPE = "manual"


@dataclass(frozen=True, slots=True)
class PersonCatalogSnapshot:
    """Stable read snapshot for one canonical person catalog row."""

    id: int
    name: str
    aliases: list[str]
    path: str | None


@dataclass(frozen=True, slots=True)
class PersonGroupCatalogSnapshot:
    """Stable read snapshot for one canonical person-group catalog row."""

    id: int
    name: str
    member_count: int


@dataclass(frozen=True, slots=True)
class PersonGroupMembershipSnapshot:
    """Stable read snapshot for one persisted member inside one group."""

    id: int
    name: str
    aliases: list[str]
    path: str | None


class ManageDataPersonRepository:
    """Repository for deterministic person-catalog maintenance."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_catalog(self) -> list[PersonCatalogSnapshot]:
        """Return the person catalog in deterministic display order."""

        statement = select(Person).order_by(func.lower(Person.name), Person.id)
        persons = self._session.execute(statement).scalars().all()
        return [
            PersonCatalogSnapshot(
                id=person.id,
                name=person.name,
                aliases=_normalize_aliases_shape(person.aliases),
                path=person.path,
            )
            for person in persons
        ]

    def get_existing_ids(self) -> set[int]:
        """Return all persisted person identifiers."""

        statement = select(Person.id)
        return set(self._session.execute(statement).scalars())

    def get_path_owner_by_path(self, *, path: str) -> Person | None:
        """Return the canonical person already owning the requested path."""

        statement = select(Person).where(Person.path == path)
        return self._session.execute(statement).scalar_one_or_none()

    def upsert_batch(self, rows: list[PersonCatalogSnapshot]) -> None:
        """Create or update the provided person rows."""

        rows_by_id = {
            row.id: row for row in rows if row.id > 0
        }
        existing_people_by_id = {
            person.id: person
            for person in self._session.execute(
                select(Person).where(Person.id.in_(rows_by_id))
            )
            .scalars()
            .all()
        }

        for row in rows:
            aliases = _normalize_aliases_shape(row.aliases)
            if row.id > 0:
                person = existing_people_by_id[row.id]
                person.name = row.name
                person.path = row.path
                person.aliases = aliases
                continue

            person = Person(
                name=row.name,
                path=row.path,
                aliases=aliases,
                metadata_json=None,
            )
            self._session.add(person)

        self._session.flush()


class ManageDataPersonGroupRepository:
    """Repository for deterministic person-group catalog maintenance."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_catalog(self) -> list[PersonGroupCatalogSnapshot]:
        """Return the person-group catalog with read-only member counts."""

        statement = (
            select(
                PersonGroup.id,
                PersonGroup.name,
                func.count(PersonGroupMember.person_id),
            )
            .outerjoin(
                PersonGroupMember,
                PersonGroupMember.group_id == PersonGroup.id,
            )
            .group_by(PersonGroup.id, PersonGroup.name)
            .order_by(func.lower(PersonGroup.name), PersonGroup.id)
        )
        return [
            PersonGroupCatalogSnapshot(
                id=group_id,
                name=name,
                member_count=member_count,
            )
            for group_id, name, member_count in self._session.execute(statement).all()
        ]

    def get_existing_ids(self) -> set[int]:
        """Return all persisted person-group identifiers."""

        statement = select(PersonGroup.id)
        return set(self._session.execute(statement).scalars())

    def get_catalog_snapshot(self, *, group_id: int) -> PersonGroupCatalogSnapshot | None:
        """Return one persisted person-group catalog row with current member count."""

        statement = (
            select(
                PersonGroup.id,
                PersonGroup.name,
                func.count(PersonGroupMember.person_id),
            )
            .outerjoin(
                PersonGroupMember,
                PersonGroupMember.group_id == PersonGroup.id,
            )
            .where(PersonGroup.id == group_id)
            .group_by(PersonGroup.id, PersonGroup.name)
        )
        row = self._session.execute(statement).one_or_none()
        if row is None:
            return None

        snapshot_group_id, name, member_count = row
        return PersonGroupCatalogSnapshot(
            id=snapshot_group_id,
            name=name,
            member_count=member_count,
        )

    def list_members(self, *, group_id: int) -> list[PersonGroupMembershipSnapshot]:
        """Return one group's persisted members in deterministic display order."""

        statement = (
            select(Person)
            .join(PersonGroupMember, PersonGroupMember.person_id == Person.id)
            .where(PersonGroupMember.group_id == group_id)
            .order_by(func.lower(Person.name), Person.id)
        )
        members = self._session.execute(statement).scalars().all()
        return [
            PersonGroupMembershipSnapshot(
                id=person.id,
                name=person.name,
                aliases=_normalize_aliases_shape(person.aliases),
                path=person.path,
            )
            for person in members
        ]

    def replace_catalog(
        self,
        *,
        upserts: list[PersonGroupCatalogSnapshot],
        delete_ids: list[int],
    ) -> None:
        """Create, update, and delete person groups plus membership links."""

        upsert_ids = {
            row.id: row for row in upserts if row.id > 0
        }
        existing_groups_by_id = {
            group.id: group
            for group in self._session.execute(
                select(PersonGroup).where(PersonGroup.id.in_(upsert_ids))
            )
            .scalars()
            .all()
        }

        for row in upserts:
            if row.id > 0:
                group = existing_groups_by_id[row.id]
                group.name = row.name
                group.type = MANUAL_PERSON_GROUP_TYPE
                continue

            self._session.add(
                PersonGroup(
                    name=row.name,
                    type=MANUAL_PERSON_GROUP_TYPE,
                    path=None,
                    metadata_json={},
                )
            )

        if delete_ids:
            self._session.execute(
                delete(PersonGroupMember).where(
                    PersonGroupMember.group_id.in_(delete_ids)
                )
            )
            self._session.execute(
                delete(PersonGroup).where(PersonGroup.id.in_(delete_ids))
            )

        self._session.flush()

    def replace_membership(self, *, group_id: int, person_ids: list[int]) -> None:
        """Replace one person group's membership links with the provided person set."""

        self._session.execute(
            delete(PersonGroupMember).where(PersonGroupMember.group_id == group_id)
        )
        for person_id in person_ids:
            self._session.add(PersonGroupMember(group_id=group_id, person_id=person_id))

        self._session.flush()


def _normalize_aliases_shape(raw_aliases: object) -> list[str]:
    """Return aliases in the explicit string-list shape used by the contract."""

    if not isinstance(raw_aliases, list):
        return []

    normalized_aliases: list[str] = []
    seen: set[str] = set()
    for value in raw_aliases:
        if not isinstance(value, str):
            continue
        alias = value.strip()
        if not alias or alias in seen:
            continue
        normalized_aliases.append(alias)
        seen.add(alias)
    return normalized_aliases
