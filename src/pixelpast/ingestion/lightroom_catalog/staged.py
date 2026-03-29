"""Lightroom catalog persistence adapters for the staged ingestion runner."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from pixelpast.ingestion.lightroom_catalog.contracts import (
    LightroomCatalogCandidate,
    LightroomCatalogDescriptor,
)
from pixelpast.ingestion.lightroom_catalog.lifecycle import (
    LightroomCatalogIngestionRunCoordinator,
)
from pixelpast.ingestion.lightroom_catalog.persist import (
    LightroomCatalogAssetPersister,
    summarize_lightroom_catalog_persistence_outcome,
)
from pixelpast.persistence.repositories import (
    AssetRepository,
    PersonRepository,
    TagRepository,
)
from pixelpast.shared.runtime import RuntimeContext


class LightroomCatalogIngestionPersistenceScope:
    """Wrap the Lightroom catalog persistence transaction boundary."""

    def __init__(
        self,
        *,
        runtime: RuntimeContext,
        lifecycle: LightroomCatalogIngestionRunCoordinator,
    ) -> None:
        session = runtime.session_factory()
        self._session = session
        self._lifecycle = lifecycle
        self._persister = LightroomCatalogAssetPersister(
            asset_repository=AssetRepository(session),
            tag_repository=TagRepository(session),
            person_repository=PersonRepository(session),
        )
        self.persisted_catalog_count = 0

    @property
    def persisted_asset_count(self) -> int:
        return self._persister.persisted_asset_count

    def count_missing_from_source(
        self,
        *,
        resolved_root: Path,
        discovered_units: Sequence[LightroomCatalogDescriptor],
        candidates: Sequence[LightroomCatalogCandidate],
    ) -> int:
        """Return the explicit v1 missing-from-source count for Lightroom assets."""

        return self._lifecycle.count_missing_from_source(
            resolved_root=resolved_root,
            discovered_catalogs=discovered_units,
            candidates=candidates,
        )

    def persist(self, *, candidate: LightroomCatalogCandidate) -> str:
        """Persist one Lightroom catalog candidate through the open session."""

        asset_outcomes = [
            self._persister.persist(asset=asset)
            for asset in candidate.assets
        ]
        self.persisted_catalog_count += 1
        return summarize_lightroom_catalog_persistence_outcome(
            asset_outcomes=asset_outcomes,
            missing_from_source_count=0,
        )

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

    def close(self) -> None:
        self._session.close()


__all__ = ["LightroomCatalogIngestionPersistenceScope"]
