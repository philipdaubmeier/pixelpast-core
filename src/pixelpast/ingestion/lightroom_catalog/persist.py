"""Canonical persistence helpers for Lightroom catalog asset candidates."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from pixelpast.ingestion.lightroom_catalog.contracts import LightroomAssetCandidate
from pixelpast.ingestion.persister_helpers import persist_asset_candidate
from pixelpast.persistence.repositories import (
    AssetRepository,
    PersonRepository,
    TagRepository,
)
from pixelpast.shared.persistence_outcome_summary import PersistenceOutcomeSummary


class LightroomCatalogAssetPersister:
    """Persist one Lightroom asset candidate through canonical repositories."""

    def __init__(
        self,
        *,
        source_id: int,
        asset_repository: AssetRepository,
        tag_repository: TagRepository,
        person_repository: PersonRepository,
    ) -> None:
        self._source_id = source_id
        self._asset_repository = asset_repository
        self._tag_repository = tag_repository
        self._person_repository = person_repository
        self.persisted_asset_count = 0

    def persist(self, *, asset: LightroomAssetCandidate) -> str:
        """Persist one canonical Lightroom asset and return its outcome."""

        self.persisted_asset_count += 1
        return persist_asset_candidate(
            source_id=self._source_id,
            asset_repository=self._asset_repository,
            tag_repository=self._tag_repository,
            person_repository=self._person_repository,
            asset=asset,
        )


def summarize_lightroom_catalog_persistence_outcome(
    *,
    asset_outcomes: Sequence[str],
    missing_from_source_count: int = 0,
) -> str:
    """Render one deterministic catalog-level persistence outcome summary."""

    counts = Counter(asset_outcomes)
    return PersistenceOutcomeSummary(
        inserted=counts.get("inserted", 0),
        updated=counts.get("updated", 0),
        unchanged=counts.get("unchanged", 0),
        missing_from_source=missing_from_source_count,
        skipped=0,
        persisted_asset_count=len(asset_outcomes),
        included_fields=frozenset({"missing_from_source"}),
    ).to_wire()
__all__ = [
    "LightroomCatalogAssetPersister",
    "summarize_lightroom_catalog_persistence_outcome",
]
