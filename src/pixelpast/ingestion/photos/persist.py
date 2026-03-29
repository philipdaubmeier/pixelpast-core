"""Photo-specific canonical asset persistence helpers."""

from __future__ import annotations

from pixelpast.ingestion.photos.contracts import PhotoAssetCandidate
from pixelpast.ingestion.persister_helpers import persist_asset_candidate
from pixelpast.persistence.repositories import (
    AssetRepository,
    PersonRepository,
    TagRepository,
)


class PhotoAssetPersister:
    """Persist one photo asset candidate through canonical repositories."""

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

    def persist(self, *, asset: PhotoAssetCandidate) -> str:
        """Persist a canonical photo asset and return its deterministic outcome."""

        return persist_asset_candidate(
            source_id=self._source_id,
            asset_repository=self._asset_repository,
            tag_repository=self._tag_repository,
            person_repository=self._person_repository,
            asset=asset,
        )


__all__ = ["PhotoAssetPersister"]
