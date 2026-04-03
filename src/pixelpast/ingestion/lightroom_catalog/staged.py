"""Lightroom catalog persistence adapters for the staged ingestion runner."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from pixelpast.ingestion.lightroom_catalog.connector import LightroomCatalogConnector
from pixelpast.ingestion.lightroom_catalog.contracts import (
    LoadedLightroomCatalog,
    LightroomCatalogCandidate,
    LightroomCatalogDescriptor,
    LightroomIngestionResult,
    LightroomTransformError,
)
from pixelpast.ingestion.lightroom_catalog.lifecycle import (
    LightroomCatalogIngestionRunCoordinator,
)
from pixelpast.ingestion.lightroom_catalog.persist import (
    LightroomCatalogAssetPersister,
    summarize_lightroom_catalog_persistence_outcome,
)
from pixelpast.ingestion.persistence_base import SessionBoundPersistenceScopeBase
from pixelpast.ingestion.lightroom_catalog.progress import (
    LightroomCatalogIngestionProgressTracker,
)
from pixelpast.persistence.repositories import (
    AssetCollectionRepository,
    AssetFolderRepository,
    AssetRepository,
    PersonRepository,
    TagRepository,
)
from pixelpast.shared.runtime import RuntimeContext


class LightroomCatalogIngestionPersistenceScope(SessionBoundPersistenceScopeBase):
    """Wrap the Lightroom catalog persistence transaction boundary."""

    def __init__(
        self,
        *,
        runtime: RuntimeContext,
        lifecycle: LightroomCatalogIngestionRunCoordinator,
        resolved_root: Path,
    ) -> None:
        super().__init__(runtime=runtime)
        self._lifecycle = lifecycle
        source_id = self._lifecycle.get_source_id(
            runtime=runtime,
            resolved_root=resolved_root,
        )
        self._persister = LightroomCatalogAssetPersister(
            source_id=source_id,
            asset_repository=AssetRepository(self._session),
            asset_folder_repository=AssetFolderRepository(self._session),
            asset_collection_repository=AssetCollectionRepository(self._session),
            tag_repository=TagRepository(self._session),
            person_repository=PersonRepository(self._session),
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

        asset_outcomes = self._persister.persist_catalog(candidate=candidate)
        self.persisted_catalog_count += 1
        return summarize_lightroom_catalog_persistence_outcome(
            asset_outcomes=asset_outcomes,
            missing_from_source_count=0,
        )


class LightroomCatalogStagedIngestionStrategy:
    """Bind the Lightroom connector to the generic staged runner contract."""

    def __init__(
        self,
        *,
        connector: LightroomCatalogConnector,
        start_index: int | None = None,
        end_index: int | None = None,
    ) -> None:
        self._connector = connector
        self._start_index = start_index
        self._end_index = end_index
        self._warning_messages: list[str] = []

    def discover_units(
        self,
        *,
        root: Path,
        on_unit_discovered,
    ) -> Sequence[LightroomCatalogDescriptor]:
        return self._connector.discover_catalogs(
            root,
            on_catalog_discovered=on_unit_discovered,
        )

    def fetch_payloads(
        self,
        *,
        units: Sequence[LightroomCatalogDescriptor],
        on_batch_progress,
    ) -> dict[LightroomCatalogDescriptor, LoadedLightroomCatalog]:
        loaded_catalogs = self._connector.fetch_catalogs(
            catalogs=units,
            start_index=self._start_index,
            end_index=self._end_index,
            on_catalog_progress=on_batch_progress,
        )
        return {
            loaded_catalog.descriptor: loaded_catalog
            for loaded_catalog in loaded_catalogs
        }

    def build_candidate(
        self,
        *,
        root: Path,
        unit: LightroomCatalogDescriptor,
        fetched_payloads: dict[LightroomCatalogDescriptor, LoadedLightroomCatalog],
    ) -> LightroomCatalogCandidate:
        del root
        candidate = self._connector.build_catalog_candidate(catalog=fetched_payloads[unit])
        self._warning_messages.extend(candidate.warning_messages)
        return candidate

    def build_transform_error(
        self,
        *,
        unit: LightroomCatalogDescriptor,
        error: Exception,
    ) -> LightroomTransformError:
        return self._connector.build_transform_error(catalog=unit, error=error)

    def describe_unit(self, *, unit: LightroomCatalogDescriptor) -> str:
        return unit.origin_label

    def build_result(
        self,
        *,
        run_id: int,
        progress: LightroomCatalogIngestionProgressTracker,
        transform_errors: Sequence[LightroomTransformError],
    ) -> LightroomIngestionResult:
        status = "partial_failure" if transform_errors else "completed"
        counters = progress.counters
        return LightroomIngestionResult(
            run_id=run_id,
            processed_catalog_count=counters.analyzed_catalog_count,
            processed_asset_count=counters.processed_asset_count,
            persisted_asset_count=counters.persisted_asset_count,
            error_count=len(transform_errors),
            status=status,
            warning_messages=tuple(self._warning_messages),
            transform_errors=tuple(transform_errors),
        )


__all__ = [
    "LightroomCatalogIngestionPersistenceScope",
    "LightroomCatalogStagedIngestionStrategy",
]
