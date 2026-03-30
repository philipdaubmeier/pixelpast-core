"""Asset thumbnail derive job composition root."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pixelpast.analytics.asset_thumbnails.loading import (
    AssetThumbnailCanonicalLoader,
    ResolvedThumbnailAsset,
)
from pixelpast.analytics.asset_thumbnails.materialization import (
    AssetThumbnailMaterializer,
)
from pixelpast.analytics.asset_thumbnails.progress import (
    ASSET_THUMBNAILS_JOB_NAME,
    AssetThumbnailProgressTracker,
)
from pixelpast.analytics.asset_thumbnails.rendering import (
    THUMBNAIL_RENDITIONS,
)
from pixelpast.analytics.lifecycle import DeriveRunCoordinator
from pixelpast.persistence.repositories import AssetMediaRepository
from pixelpast.shared.media_storage import require_media_thumb_root
from pixelpast.shared.progress import JobProgressCallback
from pixelpast.shared.runtime import RuntimeContext


@dataclass(slots=True, frozen=True)
class AssetThumbnailJobResult:
    """Summary returned by the asset thumbnail derive job."""

    run_id: int
    mode: str
    status: str
    rendition_count: int
    asset_count: int
    generated_count: int
    overwritten_count: int
    unchanged_count: int
    skipped_count: int
    failed_count: int
    warning_messages: tuple[str, ...] = ()


class AssetThumbnailJob:
    """Precompute fixed WebP thumbnails for canonical image assets."""

    def __init__(
        self,
        *,
        loader: AssetThumbnailCanonicalLoader | None = None,
        lifecycle: DeriveRunCoordinator | None = None,
        materializer: AssetThumbnailMaterializer | None = None,
    ) -> None:
        self._loader = loader or AssetThumbnailCanonicalLoader()
        self._lifecycle = lifecycle or DeriveRunCoordinator()
        self._materializer = materializer or AssetThumbnailMaterializer()

    def run(
        self,
        *,
        runtime: RuntimeContext,
        renditions: tuple[str, ...] = THUMBNAIL_RENDITIONS,
        force: bool = False,
        progress_callback: JobProgressCallback | None = None,
    ) -> AssetThumbnailJobResult:
        """Generate fixed thumbnail renditions in missing-only or force mode."""

        normalized_renditions = _normalize_renditions(renditions=renditions)
        thumb_root = require_media_thumb_root(settings=runtime.settings)
        mode = "force" if force else "missing"
        run_id = self._lifecycle.create_run(
            runtime=runtime,
            job=ASSET_THUMBNAILS_JOB_NAME,
            mode=mode,
        )
        progress = AssetThumbnailProgressTracker(
            run_id=run_id,
            runtime=runtime,
            callback=progress_callback,
        )
        session = runtime.session_factory()
        repository = AssetMediaRepository(session)

        try:
            progress.start_loading()
            assets = self._loader.load_assets(repository=repository)
            progress.mark_loading_completed(asset_count=len(assets))
            progress.finish_phase()

            total_output_count = len(assets) * len(normalized_renditions)
            progress.start_rendering(total_output_count=total_output_count)

            warning_messages: list[str] = []
            for asset in assets:
                for rendition in normalized_renditions:
                    status, warning_message = _materialize_thumbnail(
                        asset=asset,
                        rendition=rendition,
                        thumb_root=thumb_root,
                        force=force,
                        materializer=self._materializer,
                    )
                    if warning_message is not None:
                        warning_messages.append(warning_message)
                    progress.mark_output_result(status=status)

            progress.finish_phase()
            status = (
                "partial_failure" if progress.counters.failed > 0 else "completed"
            )
            progress.finish_run(status=status)
            return AssetThumbnailJobResult(
                run_id=run_id,
                mode=mode,
                status=status,
                rendition_count=len(normalized_renditions),
                asset_count=len(assets),
                generated_count=progress.counters.inserted,
                overwritten_count=progress.counters.updated,
                unchanged_count=progress.counters.unchanged,
                skipped_count=progress.counters.skipped,
                failed_count=progress.counters.failed,
                warning_messages=tuple(warning_messages),
            )
        except Exception:
            session.rollback()
            progress.fail_run()
            raise
        finally:
            session.close()


def _materialize_thumbnail(
    *,
    asset: ResolvedThumbnailAsset,
    rendition: str,
    thumb_root: Path,
    force: bool,
    materializer: AssetThumbnailMaterializer,
) -> tuple[str, str | None]:
    result = materializer.materialize(
        asset=asset,
        rendition=rendition,
        thumb_root=thumb_root,
        force=force,
    )
    return result.status, result.detail


def _normalize_renditions(
    *,
    renditions: tuple[str, ...] | list[str],
) -> tuple[str, ...]:
    if not renditions:
        return THUMBNAIL_RENDITIONS

    ordered: list[str] = []
    seen: set[str] = set()
    for rendition in renditions:
        if rendition not in THUMBNAIL_RENDITIONS:
            supported = ", ".join(THUMBNAIL_RENDITIONS)
            raise ValueError(
                f"Unsupported thumbnail rendition '{rendition}'. "
                f"Available renditions: {supported}."
            )
        if rendition in seen:
            continue
        seen.add(rendition)
        ordered.append(rendition)
    return tuple(ordered)


__all__ = [
    "ASSET_THUMBNAILS_JOB_NAME",
    "AssetThumbnailJob",
    "AssetThumbnailJobResult",
]
