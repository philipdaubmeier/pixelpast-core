"""Shared thumbnail materialization orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pixelpast.analytics.asset_thumbnails.loading import ResolvedThumbnailAsset
from pixelpast.analytics.asset_thumbnails.rendering import (
    ThumbnailRenderError,
    build_thumbnail_output_path,
    render_thumbnail,
)


@dataclass(slots=True, frozen=True)
class ThumbnailMaterializationResult:
    """Describe one thumbnail materialization attempt."""

    status: str
    output_path: Path
    detail: str | None = None
    failure_code: str | None = None


class AssetThumbnailMaterializer:
    """Materialize one fixed thumbnail rendition for one resolved asset."""

    def materialize(
        self,
        *,
        asset: ResolvedThumbnailAsset,
        rendition: str,
        thumb_root: Path,
        force: bool,
    ) -> ThumbnailMaterializationResult:
        """Render one rendition or report a deterministic skip/failure outcome."""

        output_path = build_thumbnail_output_path(
            thumb_root=thumb_root,
            rendition=rendition,
            short_id=asset.short_id,
        )
        output_exists = output_path.exists()
        if not force and output_exists:
            return ThumbnailMaterializationResult(
                status="unchanged",
                output_path=output_path,
            )

        original_path = asset.original_path
        if original_path is None:
            return ThumbnailMaterializationResult(
                status="skipped",
                output_path=output_path,
                failure_code="unsupported_asset",
                detail=(
                    "Skipping thumbnail generation for asset "
                    f"{asset.short_id} because source type {asset.source_type!r} "
                    "does not expose a resolvable original image path."
                ),
            )

        if not original_path.exists():
            return ThumbnailMaterializationResult(
                status="skipped",
                output_path=output_path,
                failure_code="missing_original",
                detail=(
                    "Skipping thumbnail generation for asset "
                    f"{asset.short_id} because the original file is missing: "
                    f"{original_path.as_posix()}"
                ),
            )

        try:
            render_thumbnail(
                source_path=original_path,
                output_path=output_path,
                rendition=rendition,
            )
        except ThumbnailRenderError as error:
            return ThumbnailMaterializationResult(
                status="failed",
                output_path=output_path,
                failure_code="render_failed",
                detail=str(error),
            )

        return ThumbnailMaterializationResult(
            status="overwritten" if output_exists else "generated",
            output_path=output_path,
        )


__all__ = [
    "AssetThumbnailMaterializer",
    "ThumbnailMaterializationResult",
]
