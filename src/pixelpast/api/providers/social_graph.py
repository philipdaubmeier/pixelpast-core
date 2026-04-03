"""Social-graph projection helpers and provider composition."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Final, Protocol

from pixelpast.api.schemas import (
    SocialGraphLink,
    SocialGraphPerson,
    SocialGraphPersonGroup,
    SocialGraphResponse,
)
from pixelpast.persistence.repositories import (
    SocialGraphReadRepository,
    SocialGraphReadSnapshot,
)


@dataclass(slots=True, frozen=True)
class SocialGraphFilters:
    """Supported server-owned filters for social-graph requests."""

    person_ids: tuple[int, ...] = ()
    person_group_ids: tuple[int, ...] = ()
    max_people_per_asset: int = 10


class SocialGraphProjectionProvider(Protocol):
    """Provide API-ready social-graph projections."""

    def get_social_graph(
        self,
        *,
        start: date | None,
        end: date | None,
        today: date,
        filters: SocialGraphFilters,
    ) -> SocialGraphResponse:
        """Return a deterministic social-graph projection."""
        ...


class DatabaseSocialGraphProjectionProvider:
    """Build social-graph projections from canonical repositories."""

    def __init__(self, *, social_graph_repository: SocialGraphReadRepository) -> None:
        self._social_graph_repository = social_graph_repository

    def get_social_graph(
        self,
        *,
        start: date | None,
        end: date | None,
        today: date,
        filters: SocialGraphFilters,
    ) -> SocialGraphResponse:
        """Return a canonical social-graph projection for the requested filters."""

        del today
        return build_social_graph_response(
            self._social_graph_repository.read_projection(
                start_date=start,
                end_date=end,
                person_ids=filters.person_ids,
                person_group_ids=filters.person_group_ids,
                max_people_per_asset=filters.max_people_per_asset,
            )
        )


class DemoSocialGraphProjectionProvider:
    """Return a deterministic social graph in demo mode."""

    def get_social_graph(
        self,
        *,
        start: date | None,
        end: date | None,
        today: date,
        filters: SocialGraphFilters,
    ) -> SocialGraphResponse:
        """Return the bounded demo social-graph payload."""

        del start, end, today

        if filters.person_group_ids:
            return SocialGraphResponse(persons=[], links=[])

        qualifying_person_ids = (
            {
                link_person_id
                for link in _DEMO_LINKS
                for link_person_id in link.person_ids
                if not filters.person_ids or link_person_id in filters.person_ids
            }
            if filters.person_ids
            else {person.id for person in _DEMO_PERSONS}
        )
        if filters.person_ids:
            qualifying_person_ids.update(filters.person_ids)
            linked_person_ids = {
                link_person_id
                for link in _DEMO_LINKS
                if set(link.person_ids).intersection(filters.person_ids)
                for link_person_id in link.person_ids
            }
            qualifying_person_ids.update(linked_person_ids)

        return SocialGraphResponse(
            persons=[
                person
                for person in _DEMO_PERSONS
                if person.id in qualifying_person_ids
            ],
            links=[
                link
                for link in _DEMO_LINKS
                if not filters.person_ids
                or set(link.person_ids).intersection(filters.person_ids)
            ],
        )


def build_social_graph_response(
    snapshot: SocialGraphReadSnapshot,
) -> SocialGraphResponse:
    """Map the canonical social-graph read snapshot to the API contract."""

    return SocialGraphResponse(
        persons=[
            SocialGraphPerson(
                id=person.id,
                name=person.name,
                occurrence_count=person.occurrence_count,
                matching_groups=[
                    SocialGraphPersonGroup(
                        id=group.id,
                        name=group.name,
                        color_index=group.color_index,
                    )
                    for group in person.matching_groups
                ],
            )
            for person in snapshot.persons
        ],
        links=[
            SocialGraphLink(
                person_ids=list(link.person_ids),
                weight=link.weight,
                affinity=round(link.affinity, 6),
            )
            for link in snapshot.links
        ],
    )


_DEMO_PERSONS: Final[tuple[SocialGraphPerson, ...]] = (
    SocialGraphPerson(id=1, name="Anna", occurrence_count=14, matching_groups=[]),
    SocialGraphPerson(id=2, name="Milo", occurrence_count=9, matching_groups=[]),
    SocialGraphPerson(id=3, name="Luca", occurrence_count=6, matching_groups=[]),
    SocialGraphPerson(id=4, name="Nora", occurrence_count=4, matching_groups=[]),
)

_DEMO_LINKS: Final[tuple[SocialGraphLink, ...]] = (
    SocialGraphLink(person_ids=[1, 2], weight=7, affinity=0.777778),
    SocialGraphLink(person_ids=[1, 3], weight=4, affinity=0.5),
    SocialGraphLink(person_ids=[2, 4], weight=2, affinity=0.333333),
)
