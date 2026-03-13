"""Service orchestration for photo asset ingestion."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pixelpast.ingestion.photos.connector import PhotoConnector
from pixelpast.persistence.repositories import (
    AssetRepository,
    ImportRunRepository,
    PersonRepository,
    SourceRepository,
    TagRepository,
)
from pixelpast.shared.runtime import RuntimeContext

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class PhotoIngestionResult:
    """Summary of a completed photo ingestion run."""

    import_run_id: int
    processed_asset_count: int
    error_count: int
    status: str


class PhotoIngestionService:
    """Coordinate photo discovery with canonical persistence."""

    def __init__(self, connector: PhotoConnector | None = None) -> None:
        self._connector = connector or PhotoConnector()

    def ingest(self, *, runtime: RuntimeContext) -> PhotoIngestionResult:
        """Run the photo connector and persist canonical assets and import state."""

        photos_root = runtime.settings.photos_root
        if photos_root is None:
            raise ValueError(
                "Photo ingestion requires PIXELPAST_PHOTOS_ROOT to be configured."
            )

        resolved_root = photos_root.expanduser().resolve()
        session = runtime.session_factory()
        source_repository = SourceRepository(session)
        import_run_repository = ImportRunRepository(session)
        asset_repository = AssetRepository(session)
        tag_repository = TagRepository(session)
        person_repository = PersonRepository(session)

        try:
            source = source_repository.get_or_create(
                name="Photos",
                source_type="photos",
                config={"root_path": resolved_root.as_posix()},
            )
            import_run = import_run_repository.create(source_id=source.id, mode="full")
            session.commit()
            import_run_id = import_run.id

            try:
                discovery = self._connector.discover(resolved_root)
                for issue in discovery.errors:
                    logger.warning(
                        "photo ingestion skipped file",
                        extra={
                            "path": issue.path.as_posix(),
                            "reason": issue.message,
                        },
                    )

                for asset in discovery.assets:
                    creator_person_id = None
                    if asset.creator_name is not None:
                        creator_person = person_repository.get_or_create(
                            name=asset.creator_name
                        )
                        creator_person_id = creator_person.id

                    asset_repository.upsert(
                        external_id=asset.external_id,
                        media_type=asset.media_type,
                        timestamp=asset.timestamp,
                        summary=asset.summary,
                        latitude=asset.latitude,
                        longitude=asset.longitude,
                        creator_person_id=creator_person_id,
                        metadata_json=asset.metadata_json,
                    )
                    persisted_asset = asset_repository.get_by_external_id(
                        external_id=asset.external_id
                    )
                    if persisted_asset is None:
                        raise RuntimeError(
                            f"Asset {asset.external_id} is missing after upsert."
                        )

                    persisted_tags = {
                        path: tag_repository.get_or_create(path=path)
                        for path in asset.tag_paths
                    }
                    asset_repository.replace_tag_links(
                        asset_id=persisted_asset.id,
                        tag_ids=[
                            persisted_tags[path].id
                            for path in asset.asset_tag_paths
                            if path in persisted_tags
                        ],
                    )

                    persisted_people = [
                        person_repository.get_or_create(
                            name=person.name,
                            path=person.path,
                        )
                        for person in asset.persons
                    ]
                    asset_repository.replace_person_links(
                        asset_id=persisted_asset.id,
                        person_ids=[person.id for person in persisted_people],
                    )

                status = "partial_failure" if discovery.errors else "completed"
                persisted_import_run = _require_import_run(
                    import_run_repository.mark_finished_by_id(
                        import_run_id=import_run_id,
                        status=status,
                    ),
                    import_run_id,
                )
                session.commit()
                return PhotoIngestionResult(
                    import_run_id=persisted_import_run.id,
                    processed_asset_count=len(discovery.assets),
                    error_count=len(discovery.errors),
                    status=status,
                )
            except Exception:
                session.rollback()
                persisted_import_run = import_run_repository.mark_finished_by_id(
                    import_run_id=import_run_id,
                    status="failed",
                )
                if persisted_import_run is not None:
                    session.commit()
                raise
        finally:
            session.close()


def _require_import_run(import_run, import_run_id: int):
    """Return a persisted import run or raise a deterministic error."""

    if import_run is None:
        raise RuntimeError(f"ImportRun {import_run_id} is missing from persistence.")
    return import_run
