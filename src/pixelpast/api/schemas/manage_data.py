"""Schemas for manage-data catalog reads and batch writes."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, StrictInt


class PersonCatalogEntry(BaseModel):
    """Readable person-catalog row exposed to the manage-data UI."""

    id: int
    name: str
    aliases: list[str]
    path: str | None


class PersonCatalogWriteEntry(BaseModel):
    """Batch-write payload row for manual person maintenance."""

    id: int | None = Field(default=None)
    name: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    path: str | None = None


class PersonsCatalogResponse(BaseModel):
    """Read response for the canonical persons catalog."""

    persons: list[PersonCatalogEntry]


class SavePersonsCatalogRequest(BaseModel):
    """Batch write request for canonical person catalog rows."""

    persons: list[PersonCatalogWriteEntry]
    delete_ids: list[int] = Field(default_factory=list)


class PersonGroupCatalogEntry(BaseModel):
    """Readable person-group catalog row exposed to the manage-data UI."""

    id: int
    name: str
    member_count: int
    ui: "PersonGroupUiEntry" = Field(default_factory=lambda: PersonGroupUiEntry())


PositiveColorIndex = Annotated[StrictInt, Field(gt=0)]


class PersonGroupUiEntry(BaseModel):
    """Explicit UI-owned person-group metadata exposed through the API."""

    color_index: PositiveColorIndex | None = None


class PersonGroupCatalogWriteEntry(BaseModel):
    """Batch-write payload row for manual person-group maintenance."""

    id: int | None = Field(default=None)
    name: str = Field(min_length=1)
    ui: PersonGroupUiEntry = Field(default_factory=PersonGroupUiEntry)


class PersonGroupAlbumAggregateRulesEntry(BaseModel):
    """Typed album-aggregate rules exposed through manage-data contracts."""

    ignored_person_ids: list[int] = Field(default_factory=list)


class PersonGroupsCatalogResponse(BaseModel):
    """Read response for the canonical person-group catalog."""

    person_groups: list[PersonGroupCatalogEntry]


class SavePersonGroupsCatalogRequest(BaseModel):
    """Batch write request for canonical person-group catalog rows."""

    person_groups: list[PersonGroupCatalogWriteEntry]
    delete_ids: list[int] = Field(default_factory=list)


class PersonGroupMembershipMemberEntry(BaseModel):
    """Readable persisted person row exposed inside one group membership editor."""

    id: int
    name: str
    aliases: list[str]
    path: str | None


class PersonGroupMembershipGroupEntry(BaseModel):
    """Readable focused person-group context for the membership editor."""

    id: int
    name: str
    member_count: int
    ui: PersonGroupUiEntry = Field(default_factory=PersonGroupUiEntry)
    album_aggregate_rules: PersonGroupAlbumAggregateRulesEntry = Field(
        default_factory=PersonGroupAlbumAggregateRulesEntry
    )


class PersonGroupMembershipResponse(BaseModel):
    """Read response for one person group's persisted membership set."""

    person_group: PersonGroupMembershipGroupEntry
    members: list[PersonGroupMembershipMemberEntry]


class SavePersonGroupMembershipRequest(BaseModel):
    """Batch replacement request for one person group's membership set."""

    person_ids: list[int] = Field(default_factory=list)
    album_aggregate_rules: PersonGroupAlbumAggregateRulesEntry = Field(
        default_factory=PersonGroupAlbumAggregateRulesEntry
    )
