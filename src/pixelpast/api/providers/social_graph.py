"""Social-graph projection helpers."""

from __future__ import annotations

from pixelpast.api.schemas import SocialGraphLink, SocialGraphPerson, SocialGraphResponse
from pixelpast.persistence.repositories import SocialGraphReadSnapshot


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
            )
            for person in snapshot.persons
        ],
        links=[
            SocialGraphLink(
                person_ids=list(link.person_ids),
                weight=link.weight,
            )
            for link in snapshot.links
        ],
    )
