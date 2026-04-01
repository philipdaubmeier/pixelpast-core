"""Photo-specific canonical asset persistence helpers."""

from __future__ import annotations

from pathlib import PurePosixPath

from pixelpast.ingestion.photos.contracts import PhotoAssetCandidate
from pixelpast.ingestion.persister_helpers import persist_asset_candidate
from pixelpast.persistence.repositories import (
    AssetFolderRepository,
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
        root_path: str,
        asset_repository: AssetRepository,
        asset_folder_repository: AssetFolderRepository,
        tag_repository: TagRepository,
        person_repository: PersonRepository,
    ) -> None:
        self._source_id = source_id
        self._root_path = root_path
        self._asset_repository = asset_repository
        self._asset_folder_repository = asset_folder_repository
        self._tag_repository = tag_repository
        self._person_repository = person_repository

    def persist(self, *, asset: PhotoAssetCandidate) -> str:
        """Persist a canonical photo asset and return its deterministic outcome."""

        folder_id = self._resolve_folder_id(asset=asset)
        return persist_asset_candidate(
            source_id=self._source_id,
            asset_repository=self._asset_repository,
            tag_repository=self._tag_repository,
            person_repository=self._person_repository,
            asset=asset,
            folder_id=folder_id,
        )

    def _resolve_folder_id(self, *, asset: PhotoAssetCandidate) -> int | None:
        metadata_json = asset.metadata_json if isinstance(asset.metadata_json, dict) else {}
        source_path = metadata_json.get("source_path")
        if not isinstance(source_path, str):
            return None

        folder_path = _build_photo_folder_path(
            source_path=source_path,
            root_path=self._root_path,
        )
        if folder_path is None:
            return None

        folder, _ = self._asset_folder_repository.get_or_create_tree(
            source_id=self._source_id,
            path=folder_path,
        )
        return folder.id


def _build_photo_folder_path(
    *,
    source_path: str | None,
    root_path: str | None,
) -> str | None:
    normalized_source_path = _normalize_path_string(source_path)
    if normalized_source_path is None:
        return None

    source_file_path = PurePosixPath(normalized_source_path)
    if source_file_path.parent == source_file_path:
        return None

    normalized_root_path = _normalize_path_string(root_path)
    if normalized_root_path is None:
        return _normalize_navigation_path(source_file_path.parent.as_posix())

    root = PurePosixPath(normalized_root_path)
    try:
        relative_parent = source_file_path.parent.relative_to(root)
    except ValueError:
        return _normalize_navigation_path(source_file_path.parent.as_posix())

    segments = [
        segment
        for segment in (root.name, *relative_parent.parts)
        if segment not in {"", "."}
    ]
    return _normalize_navigation_path("/".join(segments))


def _normalize_path_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().replace("\\", "/")
    if normalized == "":
        return None
    return normalized


def _normalize_navigation_path(value: str | None) -> str | None:
    normalized = _normalize_path_string(value)
    if normalized is None:
        return None
    segments = [segment.strip() for segment in normalized.split("/") if segment.strip() != ""]
    if not segments:
        return None
    return "/".join(segments)


__all__ = ["PhotoAssetPersister"]
