"""Canonical input loading for the album aggregate derive job."""

from __future__ import annotations

from dataclasses import dataclass

from pixelpast.persistence.repositories import (
    AlbumAggregateAssetEvidenceInput,
    AlbumAggregateCollectionMembershipInput,
    AlbumAggregateCollectionNodeInput,
    AlbumAggregateFolderNodeInput,
    AlbumAggregatePersonGroupInput,
    AlbumAggregateRepository,
)


@dataclass(slots=True, frozen=True)
class AlbumAggregateCanonicalInputs:
    """Canonical album and person-group inputs consumed by the derive builder."""

    folder_nodes: tuple[AlbumAggregateFolderNodeInput, ...]
    collection_nodes: tuple[AlbumAggregateCollectionNodeInput, ...]
    asset_evidence: tuple[AlbumAggregateAssetEvidenceInput, ...]
    collection_memberships: tuple[AlbumAggregateCollectionMembershipInput, ...]
    person_groups: tuple[AlbumAggregatePersonGroupInput, ...]


class AlbumAggregateCanonicalLoader:
    """Load the canonical inputs required by the album aggregate derive job."""

    def load_folder_nodes(
        self,
        *,
        repository: AlbumAggregateRepository,
    ) -> tuple[AlbumAggregateFolderNodeInput, ...]:
        """Return canonical folder nodes."""

        return repository.list_folder_nodes()

    def load_collection_nodes(
        self,
        *,
        repository: AlbumAggregateRepository,
    ) -> tuple[AlbumAggregateCollectionNodeInput, ...]:
        """Return canonical collection nodes."""

        return repository.list_collection_nodes()

    def load_asset_evidence(
        self,
        *,
        repository: AlbumAggregateRepository,
    ) -> tuple[AlbumAggregateAssetEvidenceInput, ...]:
        """Return per-asset person evidence."""

        return repository.list_asset_evidence()

    def load_collection_memberships(
        self,
        *,
        repository: AlbumAggregateRepository,
    ) -> tuple[AlbumAggregateCollectionMembershipInput, ...]:
        """Return direct asset-to-collection memberships."""

        return repository.list_collection_memberships()

    def load_person_groups(
        self,
        *,
        repository: AlbumAggregateRepository,
    ) -> tuple[AlbumAggregatePersonGroupInput, ...]:
        """Return person groups and their canonical membership sets."""

        return repository.list_person_groups()
