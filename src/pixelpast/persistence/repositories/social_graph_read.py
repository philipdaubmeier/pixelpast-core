"""Canonical social-graph read repository and projection snapshots."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from pixelpast.persistence.models import Asset, AssetPerson, Person
from pixelpast.persistence.repositories.daily_aggregates import _apply_datetime_range


@dataclass(slots=True, frozen=True)
class PersonAssetMembershipSnapshot:
    """Serializable membership of one person on one qualifying asset."""

    asset_id: int
    person_id: int
    person_name: str


@dataclass(slots=True, frozen=True)
class SocialGraphPersonSnapshot:
    """Serializable social-graph node snapshot."""

    id: int
    name: str
    occurrence_count: int


@dataclass(slots=True, frozen=True)
class SocialGraphLinkSnapshot:
    """Serializable unordered weighted social-graph edge snapshot."""

    person_ids: tuple[int, int]
    weight: int


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
    ) -> SocialGraphReadSnapshot:
        """Return a stable social-graph projection for qualifying assets."""

        memberships = self._list_person_asset_memberships(
            start_date=start_date,
            end_date=end_date,
            person_ids=person_ids,
        )
        return SocialGraphReadSnapshot(
            persons=self._count_person_occurrences(memberships=memberships),
            links=self._count_pair_co_occurrences(memberships=memberships),
        )

    def _list_person_asset_memberships(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        person_ids: tuple[int, ...],
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
        if person_ids:
            qualifying_asset_ids = (
                select(AssetPerson.asset_id)
                .where(AssetPerson.person_id.in_(person_ids))
                .distinct()
            )
            statement = statement.where(AssetPerson.asset_id.in_(qualifying_asset_ids))

        rows = self._session.execute(statement)
        return [
            PersonAssetMembershipSnapshot(
                asset_id=asset_id,
                person_id=person_id,
                person_name=person_name,
            )
            for asset_id, person_id, person_name in rows
        ]

    def _count_person_occurrences(
        self,
        *,
        memberships: list[PersonAssetMembershipSnapshot],
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
            SocialGraphLinkSnapshot(person_ids=person_ids, weight=weight)
            for person_ids, weight in sorted(
                pair_counts.items(),
                key=lambda item: item[0],
            )
        ]
