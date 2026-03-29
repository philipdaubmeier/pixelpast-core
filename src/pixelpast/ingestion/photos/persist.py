"""Photo-specific canonical asset persistence helpers."""

from __future__ import annotations

from pixelpast.ingestion.photos.contracts import PhotoAssetCandidate
from pixelpast.persistence.repositories import (
    AssetRepository,
    AssetUpsertResult,
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

        creator_person_id = None
        if asset.creator_name is not None:
            creator_person = self._person_repository.get_or_create(
                name=asset.creator_name
            )
            creator_person_id = creator_person.id

        upsert_result = self._asset_repository.upsert(
            source_id=self._source_id,
            external_id=asset.external_id,
            media_type=asset.media_type,
            timestamp=asset.timestamp,
            summary=asset.summary,
            latitude=asset.latitude,
            longitude=asset.longitude,
            creator_person_id=creator_person_id,
            metadata_json=asset.metadata_json,
        )
        persisted_tags = {
            path: self._tag_repository.get_or_create(path=path)
            for path in asset.tag_paths
        }
        tags_changed = self._asset_repository.replace_tag_links(
            asset_id=upsert_result.asset.id,
            tag_ids=[
                persisted_tags[path].id
                for path in asset.asset_tag_paths
                if path in persisted_tags
            ],
        )
        persisted_people = [
            self._person_repository.get_or_create(name=person.name, path=person.path)
            for person in asset.persons
        ]
        people_changed = self._asset_repository.replace_person_links(
            asset_id=upsert_result.asset.id,
            person_ids=[person.id for person in persisted_people],
        )
        return _resolve_persistence_outcome(
            upsert_result=upsert_result,
            tags_changed=tags_changed,
            people_changed=people_changed,
        )


def _resolve_persistence_outcome(
    *,
    upsert_result: AssetUpsertResult,
    tags_changed: bool,
    people_changed: bool,
) -> str:
    """Resolve the deterministic persistence outcome for one canonical asset."""

    if upsert_result.status == "inserted":
        return "inserted"
    if upsert_result.status == "updated" or tags_changed or people_changed:
        return "updated"
    return "unchanged"


__all__ = ["PhotoAssetPersister"]
