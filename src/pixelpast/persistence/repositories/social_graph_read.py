"""Canonical social-graph read repository and projection snapshots."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from math import sqrt
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pixelpast.persistence.models import (
    Asset,
    AssetPerson,
    Person,
    PersonGroup,
    PersonGroupMember,
)
from pixelpast.persistence.repositories.daily_aggregates import _apply_datetime_range


@dataclass(slots=True, frozen=True)
class PersonAssetMembershipSnapshot:
    """Serializable membership of one person on one qualifying asset."""

    asset_id: int
    person_id: int
    person_name: str


@dataclass(slots=True, frozen=True)
class SocialGraphPersonGroupSnapshot:
    """Serializable person-group metadata available for one person node."""

    id: int
    name: str
    color_index: int | None


@dataclass(slots=True, frozen=True)
class SocialGraphPersonSnapshot:
    """Serializable social-graph node snapshot."""

    id: int
    name: str
    occurrence_count: int
    matching_groups: list[SocialGraphPersonGroupSnapshot]


@dataclass(slots=True, frozen=True)
class SocialGraphLinkSnapshot:
    """Serializable unordered weighted social-graph edge snapshot."""

    person_ids: tuple[int, int]
    weight: int
    affinity: float


@dataclass(slots=True, frozen=True)
class SocialGraphReadSnapshot:
    """Serializable social-graph projection built from canonical memberships."""

    persons: list[SocialGraphPersonSnapshot]
    links: list[SocialGraphLinkSnapshot]


class SocialGraphReadRepository:
    """Read a person co-occurrence graph directly from canonical asset links."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def read_projection(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        person_ids: tuple[int, ...] = (),
        person_group_ids: tuple[int, ...] = (),
        max_people_per_asset: int = 10,
    ) -> SocialGraphReadSnapshot:
        """Return a stable social-graph projection for qualifying assets."""

        filtered_person_ids = self._list_selected_group_member_ids(
            person_group_ids=person_group_ids
        )
        if person_group_ids and not filtered_person_ids:
            return SocialGraphReadSnapshot(persons=[], links=[])

        memberships = self._list_person_asset_memberships(
            start_date=start_date,
            end_date=end_date,
            person_ids=person_ids,
            filtered_person_ids=filtered_person_ids,
            max_people_per_asset=max_people_per_asset,
        )
        matching_groups_by_person_id = self._list_matching_groups_by_person_id(
            person_ids={membership.person_id for membership in memberships}
        )
        persons = self._count_person_occurrences(
            memberships=memberships,
            matching_groups_by_person_id=matching_groups_by_person_id,
        )
        occurrence_count_by_person_id = {
            person.id: person.occurrence_count
            for person in persons
        }
        return SocialGraphReadSnapshot(
            persons=persons,
            links=self._count_pair_co_occurrences(
                memberships=memberships,
                occurrence_count_by_person_id=occurrence_count_by_person_id,
            ),
        )

    def _list_person_asset_memberships(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        person_ids: tuple[int, ...],
        filtered_person_ids: set[int] | None,
        max_people_per_asset: int,
    ) -> list[PersonAssetMembershipSnapshot]:
        """Load all qualifying canonical person memberships across assets."""

        statement = (
            select(AssetPerson.asset_id, Person.id, Person.name)
            .join(Asset, Asset.id == AssetPerson.asset_id)
            .join(Person, Person.id == AssetPerson.person_id)
            .order_by(Asset.timestamp, AssetPerson.asset_id, Person.name, Person.id)
        )
        if start_date is not None and end_date is not None:
            statement = _apply_datetime_range(
                statement,
                column=Asset.timestamp,
                start_date=start_date,
                end_date=end_date,
            )

        qualifying_group_asset_ids = (
            select(AssetPerson.asset_id)
            .group_by(AssetPerson.asset_id)
            .having(func.count(AssetPerson.person_id) <= max_people_per_asset)
        )
        statement = statement.where(AssetPerson.asset_id.in_(qualifying_group_asset_ids))

        if person_ids:
            qualifying_asset_ids = (
                select(AssetPerson.asset_id)
                .where(AssetPerson.person_id.in_(person_ids))
                .distinct()
            )
            statement = statement.where(AssetPerson.asset_id.in_(qualifying_asset_ids))
        if filtered_person_ids is not None:
            statement = statement.where(Person.id.in_(filtered_person_ids))

        rows = self._session.execute(statement)
        return [
            PersonAssetMembershipSnapshot(
                asset_id=asset_id,
                person_id=person_id,
                person_name=person_name,
            )
            for asset_id, person_id, person_name in rows
        ]

    def _list_selected_group_member_ids(
        self,
        *,
        person_group_ids: tuple[int, ...],
    ) -> set[int] | None:
        """Return the canonical person ids matching the selected group filter."""

        if not person_group_ids:
            return None

        statement = select(PersonGroupMember.person_id).where(
            PersonGroupMember.group_id.in_(person_group_ids)
        )
        return set(self._session.execute(statement).scalars())

    def _list_matching_groups_by_person_id(
        self,
        *,
        person_ids: set[int],
    ) -> dict[int, list[SocialGraphPersonGroupSnapshot]]:
        """Return deterministic matching person-group metadata for projected nodes."""

        if not person_ids:
            return {}

        statement = (
            select(
                PersonGroupMember.person_id,
                PersonGroup.id,
                PersonGroup.name,
                PersonGroup.metadata_json,
            )
            .join(PersonGroup, PersonGroup.id == PersonGroupMember.group_id)
            .where(PersonGroupMember.person_id.in_(person_ids))
            .order_by(
                PersonGroupMember.person_id,
                func.lower(PersonGroup.name),
                PersonGroup.id,
            )
        )
        matching_groups_by_person_id: dict[int, list[SocialGraphPersonGroupSnapshot]] = (
            defaultdict(list)
        )
        for person_id, group_id, group_name, metadata_json in self._session.execute(
            statement
        ):
            matching_groups_by_person_id[person_id].append(
                SocialGraphPersonGroupSnapshot(
                    id=group_id,
                    name=group_name,
                    color_index=_normalize_person_group_color_index(metadata_json),
                )
            )
        return dict(matching_groups_by_person_id)

    def _count_person_occurrences(
        self,
        *,
        memberships: list[PersonAssetMembershipSnapshot],
        matching_groups_by_person_id: dict[int, list[SocialGraphPersonGroupSnapshot]],
    ) -> list[SocialGraphPersonSnapshot]:
        """Count how often each person appears on qualifying assets."""

        person_counts: Counter[tuple[int, str]] = Counter(
            (membership.person_id, membership.person_name)
            for membership in memberships
        )
        return [
            SocialGraphPersonSnapshot(
                id=person_id,
                name=person_name,
                occurrence_count=occurrence_count,
                matching_groups=matching_groups_by_person_id.get(person_id, []),
            )
            for (person_id, person_name), occurrence_count in sorted(
                person_counts.items(),
                key=lambda item: (item[0][1].casefold(), item[0][0]),
            )
        ]

    def _count_pair_co_occurrences(
        self,
        *,
        memberships: list[PersonAssetMembershipSnapshot],
        occurrence_count_by_person_id: dict[int, int],
    ) -> list[SocialGraphLinkSnapshot]:
        """Count unordered person-pair co-occurrences across qualifying assets."""

        person_ids_by_asset_id: dict[int, set[int]] = defaultdict(set)
        for membership in memberships:
            person_ids_by_asset_id[membership.asset_id].add(membership.person_id)

        pair_counts: Counter[tuple[int, int]] = Counter()
        for asset_id in sorted(person_ids_by_asset_id):
            ordered_person_ids = sorted(person_ids_by_asset_id[asset_id])
            for left_index, left_person_id in enumerate(ordered_person_ids[:-1]):
                for right_person_id in ordered_person_ids[left_index + 1 :]:
                    pair_counts[(left_person_id, right_person_id)] += 1

        return [
            SocialGraphLinkSnapshot(
                person_ids=person_ids,
                weight=weight,
                affinity=_calculate_context_affinity(
                    co_occurrence_count=weight,
                    left_occurrence_count=occurrence_count_by_person_id[person_ids[0]],
                    right_occurrence_count=occurrence_count_by_person_id[person_ids[1]],
                ),
            )
            for person_ids, weight in sorted(
                pair_counts.items(),
                key=lambda item: item[0],
            )
        ]


def _normalize_person_group_color_index(metadata_json: Any) -> int | None:
    """Return the persisted positive UI color index when present."""

    if not isinstance(metadata_json, dict):
        return None
    ui_metadata = metadata_json.get("ui")
    if not isinstance(ui_metadata, dict):
        return None
    color_index = ui_metadata.get("color_index")
    if (
        not isinstance(color_index, int)
        or isinstance(color_index, bool)
        or color_index <= 0
    ):
        return None
    return color_index


def _calculate_context_affinity(
    *,
    co_occurrence_count: int,
    left_occurrence_count: int,
    right_occurrence_count: int,
) -> float:
    """Score pair affinity from overlap exclusivity plus repeated evidence.

    The score intentionally penalizes hub-like people who appear in many unrelated
    contexts while preserving strong ties for smaller, exclusive groups.
    """

    if co_occurrence_count <= 0:
        return 0.0

    safe_left_count = max(left_occurrence_count, 1)
    safe_right_count = max(right_occurrence_count, 1)
    overlap = co_occurrence_count / min(safe_left_count, safe_right_count)
    union = safe_left_count + safe_right_count - co_occurrence_count
    jaccard = co_occurrence_count / max(union, 1)
    evidence = co_occurrence_count / (co_occurrence_count + 2)

    return sqrt(overlap * jaccard) * evidence
