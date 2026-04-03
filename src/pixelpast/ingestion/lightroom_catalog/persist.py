"""Canonical persistence helpers for Lightroom catalog asset candidates."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from pixelpast.ingestion.lightroom_catalog.contracts import (
    LightroomAssetCandidate,
    LightroomCatalogCandidate,
    LightroomCollectionNode,
)
from pixelpast.ingestion.persister_helpers import persist_asset_candidate
from pixelpast.persistence.repositories import (
    AssetCollectionRepository,
    AssetFolderRepository,
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
        asset_folder_repository: AssetFolderRepository,
        asset_collection_repository: AssetCollectionRepository,
        tag_repository: TagRepository,
        person_repository: PersonRepository,
    ) -> None:
        self._source_id = source_id
        self._asset_repository = asset_repository
        self._asset_folder_repository = asset_folder_repository
        self._asset_collection_repository = asset_collection_repository
        self._tag_repository = tag_repository
        self._person_repository = person_repository
        self.persisted_asset_count = 0

    def persist_catalog(self, *, candidate: LightroomCatalogCandidate) -> list[str]:
        """Persist one Lightroom catalog candidate and reconcile album navigation."""

        try:
            self._persist_collection_tree(collections=candidate.collections)
        except Exception as error:
            raise RuntimeError(
                "Failed to persist Lightroom collection tree for catalog "
                f"'{candidate.catalog.origin_label}': {error}"
            ) from error

        asset_outcomes: list[str] = []
        membership_pairs: set[tuple[int, int]] = set()
        persisted_asset_ids: set[int] = set()
        for asset in candidate.assets:
            try:
                self.persisted_asset_count += 1
                outcome = persist_asset_candidate(
                    source_id=self._source_id,
                    asset_repository=self._asset_repository,
                    tag_repository=self._tag_repository,
                    person_repository=self._person_repository,
                    asset=asset,
                    folder_id=self._resolve_folder_id(asset=asset),
                )
                asset_outcomes.append(outcome)
                persisted_asset = self._asset_repository.get_by_source_and_external_id(
                    source_id=self._source_id,
                    external_id=asset.external_id,
                )
                if persisted_asset is None:
                    raise RuntimeError(
                        "Persisted Lightroom asset could not be reloaded by external id."
                    )
                persisted_asset_ids.add(persisted_asset.id)
                for collection in asset.collections:
                    persisted_collection = (
                        self._asset_collection_repository.get_by_source_and_external_id(
                            source_id=self._source_id,
                            external_id=str(collection.collection_id),
                        )
                    )
                    if persisted_collection is None:
                        raise RuntimeError(
                            "Persisted Lightroom collection could not be reloaded by external id."
                        )
                    membership_pairs.add((persisted_collection.id, persisted_asset.id))
            except Exception as error:
                raise RuntimeError(
                    "Failed to persist Lightroom asset "
                    f"'{asset.external_id}' from catalog "
                    f"'{candidate.catalog.origin_label}': {error}"
                ) from error

        try:
            self._asset_collection_repository.replace_items_for_assets(
                source_id=self._source_id,
                asset_ids=persisted_asset_ids,
                memberships=membership_pairs,
            )
        except Exception as error:
            raise RuntimeError(
                "Failed to reconcile Lightroom collection memberships for catalog "
                f"'{candidate.catalog.origin_label}': {error}"
            ) from error
        return asset_outcomes

    def _resolve_folder_id(self, *, asset: LightroomAssetCandidate) -> int | None:
        if asset.folder_path is None:
            return None
        folder, _ = self._asset_folder_repository.get_or_create_tree(
            source_id=self._source_id,
            path=asset.folder_path,
        )
        return folder.id

    def _persist_collection_tree(
        self,
        *,
        collections: Sequence[LightroomCollectionNode],
    ) -> None:
        for collection in collections:
            self._asset_collection_repository.upsert(
                source_id=self._source_id,
                external_id=str(collection.collection_id),
                name=collection.collection_name,
                path=collection.collection_path,
                collection_type=collection.collection_type,
                metadata_json=None,
            )
        self._asset_collection_repository.reconcile_parent_links(
            source_id=self._source_id
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
