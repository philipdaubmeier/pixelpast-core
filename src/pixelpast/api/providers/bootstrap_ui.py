"""Bootstrap UI projection helpers."""

from __future__ import annotations

from datetime import date
from typing import Final

from pixelpast.api.schemas import (
    ExplorationBootstrapResponse,
    ExplorationPerson,
    ExplorationRange,
    ExplorationTag,
    ExplorationViewMode,
)
from pixelpast.persistence.repositories import DayPersonLinkSnapshot, DayTagLinkSnapshot

_VIEW_MODE_DEFINITIONS: Final[tuple[tuple[str, str, str], ...]] = (
    (
        "activity",
        "Activity",
        "Default heat intensity across all timeline sources.",
    ),
    (
        "photos",
        "Photos",
        "Highlights days with a large number of photos.",
    ),
    (
        "videos",
        "Videos",
        "Highlights days with a large number of videos.",
    ),
    (
        "music",
        "Music",
        "Highlights days with a large number of music tracks.",
    ),
    (
        "calendar",
        "Calendar",
        "Highlights days with calendar events.",
    ),
    (
        "sports",
        "Sports",
        "Highlights days with sports activities.",
    ),
)


def build_bootstrap_response(
    *,
    start: date,
    end: date,
    person_links: list[DayPersonLinkSnapshot],
    tag_links: list[DayTagLinkSnapshot],
) -> ExplorationBootstrapResponse:
    """Compose the exploration bootstrap payload."""

    return ExplorationBootstrapResponse(
        range=ExplorationRange(start=start, end=end),
        view_modes=get_default_view_modes(),
        persons=build_person_catalog(person_links),
        tags=build_tag_catalog(tag_links),
    )


def get_default_view_modes() -> list[ExplorationViewMode]:
    """Return the backend-defined exploration view modes."""

    return [
        ExplorationViewMode(
            id=mode_id,
            label=label,
            description=description,
        )
        for mode_id, label, description in _VIEW_MODE_DEFINITIONS
    ]


def build_person_catalog(
    links: list[DayPersonLinkSnapshot],
) -> list[ExplorationPerson]:
    """Build the visible person catalog from canonical associations."""

    persons_by_id: dict[int, ExplorationPerson] = {}

    for link in links:
        persons_by_id.setdefault(
            link.person_id,
            ExplorationPerson(
                id=link.person_id,
                name=link.person_name,
                role=link.person_role,
            ),
        )

    return sorted(
        persons_by_id.values(),
        key=lambda person: (person.name.casefold(), person.id),
    )


def build_tag_catalog(
    links: list[DayTagLinkSnapshot],
) -> list[ExplorationTag]:
    """Build the visible tag catalog from canonical associations."""

    tags_by_path: dict[str, ExplorationTag] = {}

    for link in links:
        tags_by_path.setdefault(
            link.tag_path,
            ExplorationTag(path=link.tag_path, label=link.tag_label),
        )

    return sorted(
        tags_by_path.values(),
        key=lambda tag: (tag.path, tag.label.casefold()),
    )
