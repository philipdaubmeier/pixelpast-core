"""Service layer for manage-data catalog reads and writes."""

from __future__ import annotations

from pixelpast.api.schemas.manage_data import (
    PersonCatalogEntry,
    PersonCatalogWriteEntry,
    PersonGroupCatalogEntry,
    PersonGroupCatalogWriteEntry,
    PersonGroupsCatalogResponse,
    PersonsCatalogResponse,
)
from pixelpast.persistence.repositories.manage_data import (
    ManageDataPersonGroupRepository,
    ManageDataPersonRepository,
    PersonCatalogSnapshot,
    PersonGroupCatalogSnapshot,
)


class ManageDataValidationError(ValueError):
    """Raised when a manage-data write violates a contract rule."""


class ManageDataCatalogService:
    """Coordinate explicit manage-data catalog queries and writes."""

    def __init__(
        self,
        *,
        person_repository: ManageDataPersonRepository,
        person_group_repository: ManageDataPersonGroupRepository,
    ) -> None:
        self._person_repository = person_repository
        self._person_group_repository = person_group_repository

    def get_persons_catalog(self) -> PersonsCatalogResponse:
        """Return the persisted persons catalog."""

        return PersonsCatalogResponse(
            persons=[
                PersonCatalogEntry(
                    id=snapshot.id,
                    name=snapshot.name,
                    aliases=list(snapshot.aliases),
                    path=snapshot.path,
                )
                for snapshot in self._person_repository.list_catalog()
            ]
        )

    def save_persons_catalog(
        self,
        *,
        persons: list[PersonCatalogWriteEntry],
        delete_ids: list[int],
    ) -> PersonsCatalogResponse:
        """Create and update persons while rejecting deletion semantics."""

        if delete_ids:
            raise ManageDataValidationError(
                "person deletion is not supported in the v1 manage-data contract"
            )

        normalized_rows = [
            _normalize_person_write_entry(row)
            for row in persons
        ]
        self._validate_person_identifiers(rows=normalized_rows)
        self._validate_person_paths(rows=normalized_rows)
        self._person_repository.upsert_batch(normalized_rows)
        return self.get_persons_catalog()

    def get_person_groups_catalog(self) -> PersonGroupsCatalogResponse:
        """Return the persisted person-group catalog with member counts."""

        return PersonGroupsCatalogResponse(
            person_groups=[
                PersonGroupCatalogEntry(
                    id=snapshot.id,
                    name=snapshot.name,
                    member_count=snapshot.member_count,
                )
                for snapshot in self._person_group_repository.list_catalog()
            ]
        )

    def save_person_groups_catalog(
        self,
        *,
        person_groups: list[PersonGroupCatalogWriteEntry],
        delete_ids: list[int],
    ) -> PersonGroupsCatalogResponse:
        """Create, update, and delete manual person groups."""

        normalized_rows = [
            _normalize_person_group_write_entry(row)
            for row in person_groups
        ]
        self._validate_person_group_identifiers(
            rows=normalized_rows,
            delete_ids=delete_ids,
        )
        self._person_group_repository.replace_catalog(
            upserts=normalized_rows,
            delete_ids=sorted(set(delete_ids)),
        )
        return self.get_person_groups_catalog()

    def _validate_person_identifiers(
        self,
        *,
        rows: list[PersonCatalogSnapshot],
    ) -> None:
        existing_ids = self._person_repository.get_existing_ids()
        for row in rows:
            if row.id > 0 and row.id not in existing_ids:
                raise ManageDataValidationError(
                    f"person id {row.id} does not exist"
                )

    def _validate_person_paths(
        self,
        *,
        rows: list[PersonCatalogSnapshot],
    ) -> None:
        seen_paths: dict[str, int] = {}
        for row in rows:
            if row.path is None:
                continue
            if row.path in seen_paths and seen_paths[row.path] != row.id:
                raise ManageDataValidationError(
                    f"person path '{row.path}' must be unique"
                )
            seen_paths[row.path] = row.id

            owner = self._person_repository.get_path_owner_by_path(path=row.path)
            if owner is not None and owner.id != row.id:
                raise ManageDataValidationError(
                    f"person path '{row.path}' must be unique"
                )

    def _validate_person_group_identifiers(
        self,
        *,
        rows: list[PersonGroupCatalogSnapshot],
        delete_ids: list[int],
    ) -> None:
        existing_ids = self._person_group_repository.get_existing_ids()
        upsert_ids = {row.id for row in rows if row.id > 0}
        overlap_ids = sorted(upsert_ids & set(delete_ids))
        if overlap_ids:
            raise ManageDataValidationError(
                "person groups cannot be updated and deleted in the same batch"
            )
        for row in rows:
            if row.id > 0 and row.id not in existing_ids:
                raise ManageDataValidationError(
                    f"person group id {row.id} does not exist"
                )
        for group_id in set(delete_ids):
            if group_id not in existing_ids:
                raise ManageDataValidationError(
                    f"person group id {group_id} does not exist"
                )


def _normalize_person_write_entry(row: PersonCatalogWriteEntry) -> PersonCatalogSnapshot:
    name = row.name.strip()
    if not name:
        raise ManageDataValidationError("person name must not be blank")

    normalized_aliases: list[str] = []
    seen_aliases: set[str] = set()
    for alias in row.aliases:
        normalized_alias = alias.strip()
        if not normalized_alias or normalized_alias in seen_aliases:
            continue
        normalized_aliases.append(normalized_alias)
        seen_aliases.add(normalized_alias)

    path = row.path.strip() if row.path is not None else None
    if path == "":
        path = None

    return PersonCatalogSnapshot(
        id=row.id or 0,
        name=name,
        aliases=normalized_aliases,
        path=path,
    )


def _normalize_person_group_write_entry(
    row: PersonGroupCatalogWriteEntry,
) -> PersonGroupCatalogSnapshot:
    name = row.name.strip()
    if not name:
        raise ManageDataValidationError("person group name must not be blank")

    return PersonGroupCatalogSnapshot(
        id=row.id or 0,
        name=name,
        member_count=0,
    )
