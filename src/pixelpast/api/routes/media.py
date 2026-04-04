"""Short-id-based media delivery routes."""

from __future__ import annotations

import mimetypes
from os import PathLike
from pathlib import Path
from typing import Final

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from pixelpast.analytics.asset_thumbnails.loading import AssetThumbnailCanonicalLoader
from pixelpast.analytics.asset_thumbnails.materialization import (
    AssetThumbnailMaterializer,
)
from pixelpast.analytics.asset_thumbnails.rendering import (
    THUMBNAIL_RENDITIONS,
    build_thumbnail_output_path,
)
from pixelpast.api.routes.metadata import combine_responses
from pixelpast.api.schemas.errors import ApiErrorResponse
from pixelpast.persistence.repositories import (
    AssetMediaRepository,
    AssetOriginalCandidate,
)
from pixelpast.shared.media_storage import require_media_thumb_root
from pixelpast.shared.settings import Settings

router = APIRouter(tags=["media"])

_THUMBNAIL_LOADER: Final[AssetThumbnailCanonicalLoader] = (
    AssetThumbnailCanonicalLoader()
)
_THUMBNAIL_MATERIALIZER: Final[AssetThumbnailMaterializer] = (
    AssetThumbnailMaterializer()
)

THUMBNAIL_SUCCESS_EXAMPLES = {
    "cached_h120": {
        "summary": "Cached fixed-height thumbnail hit",
        "value": "<<binary image/webp body>>",
    }
}

THUMBNAIL_NOT_FOUND_EXAMPLES = {
    "unknown_short_id": {
        "summary": "Unknown asset short id",
        "value": {"detail": "asset short id 'MISS0001' does not exist"},
    },
    "missing_original": {
        "summary": "Original file missing during lazy generation",
        "value": {"detail": "original file for asset 'PHOTO001' is missing"},
    },
}

THUMBNAIL_UNSUPPORTED_EXAMPLES = {
    "unsupported_asset": {
        "summary": "Asset cannot produce an image thumbnail",
        "value": {"detail": "asset 'TRACK001' does not support image thumbnails"},
    },
    "render_failed": {
        "summary": "Stored source cannot be rendered as an image",
        "value": {"detail": "asset 'BROKEN01' could not be rendered as a thumbnail"},
    },
}

THUMBNAIL_RESPONSES = combine_responses(
    {
        200: {
            "description": "Fixed WebP thumbnail for the requested asset short id.",
            "content": {
                "image/webp": {
                    "examples": THUMBNAIL_SUCCESS_EXAMPLES,
                }
            },
        },
        404: {
            "model": ApiErrorResponse,
            "description": (
                "No matching asset exists for the short id, or the original file "
                "required for lazy generation is missing."
            ),
            "content": {
                "application/json": {
                    "examples": THUMBNAIL_NOT_FOUND_EXAMPLES,
                }
            },
        },
        415: {
            "model": ApiErrorResponse,
            "description": (
                "The resolved asset does not support image-thumbnail generation or "
                "its source image cannot be rendered."
            ),
            "content": {
                "application/json": {
                    "examples": THUMBNAIL_UNSUPPORTED_EXAMPLES,
                }
            },
        },
    }
)

ORIGINAL_SUCCESS_EXAMPLES = {
    "jpeg_inline": {
        "summary": "Original image with preserved filename",
        "value": "<<binary original image body>>",
    }
}

ORIGINAL_NOT_FOUND_EXAMPLES = {
    "unknown_short_id": {
        "summary": "Unknown asset short id",
        "value": {"detail": "asset short id 'MISS0001' does not exist"},
    },
    "unresolved_original_path": {
        "summary": "Canonical asset cannot resolve to an original file path",
        "value": {
            "detail": "original file path for asset 'BROKEN01' could not be resolved"
        },
    },
    "missing_original": {
        "summary": "Resolved original file no longer exists on disk",
        "value": {"detail": "original file for asset 'PHOTO404' is missing"},
    },
}

ORIGINAL_RESPONSES = combine_responses(
    {
        200: {
            "description": (
                "Original media file resolved from canonical asset provenance for "
                "the requested asset short id."
            ),
            "content": {
                "image/*": {
                    "examples": ORIGINAL_SUCCESS_EXAMPLES,
                },
                "application/octet-stream": {
                    "examples": ORIGINAL_SUCCESS_EXAMPLES,
                },
            },
            "headers": {
                "Content-Disposition": {
                    "description": (
                        "Inline disposition header preserving the original filename "
                        "for browser open and download behavior."
                    ),
                    "schema": {
                        "type": "string",
                    },
                    "example": 'inline; filename="IMG_1042.JPG"',
                }
            },
        },
        404: {
            "model": ApiErrorResponse,
            "description": (
                "No matching asset exists for the short id, the canonical asset "
                "cannot resolve to an original file path, or the resolved file is "
                "missing on disk."
            ),
            "content": {
                "application/json": {
                    "examples": ORIGINAL_NOT_FOUND_EXAMPLES,
                }
            },
        },
    }
)


@router.get(
    "/media/h120/{short_id}.webp",
    summary="Get h120 WebP thumbnail",
    description=(
        "Return the fixed `h120` WebP thumbnail for one asset short id. Existing "
        "thumbnail files are served directly from the configured thumbnail root "
        "without a canonical database lookup. On cache miss, the API resolves the "
        "asset by short id and lazily generates the missing rendition."
    ),
    response_class=FileResponse,
    responses=THUMBNAIL_RESPONSES,
)
def get_h120_thumbnail(short_id: str, request: Request) -> FileResponse:
    """Serve the fixed `h120` WebP thumbnail for one asset short id."""

    return _serve_thumbnail(short_id=short_id, rendition="h120", request=request)


@router.get(
    "/media/h240/{short_id}.webp",
    summary="Get h240 WebP thumbnail",
    description=(
        "Return the fixed `h240` WebP thumbnail for one asset short id. Existing "
        "thumbnail files are served directly from the configured thumbnail root "
        "without a canonical database lookup. On cache miss, the API resolves the "
        "asset by short id and lazily generates the missing rendition."
    ),
    response_class=FileResponse,
    responses=THUMBNAIL_RESPONSES,
)
def get_h240_thumbnail(short_id: str, request: Request) -> FileResponse:
    """Serve the fixed `h240` WebP thumbnail for one asset short id."""

    return _serve_thumbnail(short_id=short_id, rendition="h240", request=request)


@router.get(
    "/media/q200/{short_id}.webp",
    summary="Get q200 WebP thumbnail",
    description=(
        "Return the fixed `q200` WebP thumbnail for one asset short id. Existing "
        "thumbnail files are served directly from the configured thumbnail root "
        "without a canonical database lookup. On cache miss, the API resolves the "
        "asset by short id and lazily generates the missing rendition."
    ),
    response_class=FileResponse,
    responses=THUMBNAIL_RESPONSES,
)
def get_q200_thumbnail(short_id: str, request: Request) -> FileResponse:
    """Serve the fixed `q200` WebP thumbnail for one asset short id."""

    return _serve_thumbnail(short_id=short_id, rendition="q200", request=request)


@router.get(
    "/media/orig/{short_id}",
    summary="Get original media file",
    description=(
        "Resolve one canonical asset through the database by public short id and "
        "serve its original media file from persisted source-aware provenance. "
        "Unlike thumbnail routes, this endpoint is allowed to pay the canonical "
        "lookup cost and preserves the original filename through "
        "`Content-Disposition`."
    ),
    response_class=FileResponse,
    responses=ORIGINAL_RESPONSES,
)
def get_original_media(short_id: str, request: Request) -> FileResponse:
    """Serve the original media file for one asset short id."""

    session_factory = request.app.state.session_factory
    session = session_factory()
    try:
        repository = AssetMediaRepository(session)
        candidate = repository.get_original_candidate_by_short_id(short_id=short_id)
    finally:
        session.close()

    if candidate is None:
        raise HTTPException(
            status_code=404,
            detail=f"asset short id '{short_id}' does not exist",
        )

    original_path = _resolve_original_path(candidate=candidate)
    if original_path is None:
        raise HTTPException(
            status_code=404,
            detail=f"original file path for asset '{short_id}' could not be resolved",
        )

    delivery_path = _resolve_original_delivery_path(original_path=original_path)
    if delivery_path is None:
        raise HTTPException(
            status_code=404,
            detail=f"original file for asset '{short_id}' is missing",
        )

    filename = _resolve_original_filename(
        candidate=candidate,
        original_path=delivery_path,
    )
    return _build_original_file_response(
        output_path=delivery_path,
        filename=filename,
    )


def _serve_thumbnail(
    *,
    short_id: str,
    rendition: str,
    request: Request,
) -> FileResponse:
    if rendition not in THUMBNAIL_RENDITIONS:
        raise HTTPException(status_code=404, detail="unknown thumbnail rendition")

    settings: Settings = request.app.state.settings
    thumb_root = require_media_thumb_root(settings=settings)
    output_path = build_thumbnail_output_path(
        thumb_root=thumb_root,
        rendition=rendition,
        short_id=short_id,
    )
    if output_path.exists():
        return _build_file_response(output_path=output_path)

    session_factory = request.app.state.session_factory
    session = session_factory()
    try:
        repository = AssetMediaRepository(session)
        candidate = repository.get_thumbnail_candidate_by_short_id(short_id=short_id)
        if candidate is None:
            raise HTTPException(
                status_code=404,
                detail=f"asset short id '{short_id}' does not exist",
            )

        asset = _THUMBNAIL_LOADER.resolve_asset(candidate)
        result = _THUMBNAIL_MATERIALIZER.materialize(
            asset=asset,
            rendition=rendition,
            thumb_root=thumb_root,
            force=False,
        )
    finally:
        session.close()

    if result.status in {"generated", "overwritten", "unchanged"}:
        return _build_file_response(output_path=result.output_path)

    if result.failure_code == "missing_original":
        raise HTTPException(
            status_code=404,
            detail=f"original file for asset '{short_id}' is missing",
        )

    if result.failure_code == "unsupported_asset":
        raise HTTPException(
            status_code=415,
            detail=f"asset '{short_id}' does not support image thumbnails",
        )

    raise HTTPException(
        status_code=415,
        detail=f"asset '{short_id}' could not be rendered as a thumbnail",
    )


def _build_file_response(*, output_path: str | bytes | PathLike[str]) -> FileResponse:
    return FileResponse(path=output_path, media_type="image/webp")


def _build_original_file_response(
    *,
    output_path: str | bytes | PathLike[str],
    filename: str,
) -> FileResponse:
    media_type = (
        mimetypes.guess_type(str(output_path))[0] or "application/octet-stream"
    )
    return FileResponse(
        path=output_path,
        media_type=media_type,
        filename=filename,
        content_disposition_type="inline",
    )


def _resolve_original_path(*, candidate: AssetOriginalCandidate) -> Path | None:
    metadata = (
        candidate.metadata_json
        if isinstance(candidate.metadata_json, dict)
        else {}
    )

    if candidate.source_type == "photos":
        source_path = metadata.get("source_path")
        if isinstance(source_path, str) and source_path.strip():
            return Path(source_path)
        if candidate.external_id.strip():
            return Path(candidate.external_id)
        return None

    if candidate.source_type == "lightroom_catalog":
        file_path = metadata.get("file_path")
        if isinstance(file_path, str) and file_path.strip():
            return Path(file_path)
        return None

    return None


def _resolve_original_delivery_path(*, original_path: Path) -> Path | None:
    if original_path.is_file():
        jpg_fallback_path = _resolve_same_basename_jpg_path(source_path=original_path)
        if jpg_fallback_path is not None:
            return jpg_fallback_path
        return original_path

    return _resolve_same_basename_jpg_path(source_path=original_path)


def _resolve_same_basename_jpg_path(*, source_path: Path) -> Path | None:
    jpg_fallback_path = source_path.with_suffix(".jpg")
    if jpg_fallback_path == source_path or not jpg_fallback_path.is_file():
        return None
    return jpg_fallback_path


def _resolve_original_filename(
    *,
    candidate: AssetOriginalCandidate,
    original_path: Path,
) -> str:
    metadata = (
        candidate.metadata_json
        if isinstance(candidate.metadata_json, dict)
        else {}
    )
    preferred_names = (
        metadata.get("preserved_file_name"),
        metadata.get("file_name"),
        metadata.get("filename"),
    )
    for value in preferred_names:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return original_path.name or f"{candidate.short_id}.bin"
