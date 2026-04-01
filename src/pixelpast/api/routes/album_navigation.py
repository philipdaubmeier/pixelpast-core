"""Routes for album-navigation trees and album asset listings."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from pixelpast.api.dependencies import get_db_session
from pixelpast.api.routes.metadata import (
    BAD_REQUEST_RESPONSE,
    VALIDATION_ERROR_RESPONSE,
    combine_responses,
)
from pixelpast.api.schemas import (
    AlbumAssetDetailResponse,
    AlbumAssetListingResponse,
    AlbumCollectionsTreeResponse,
    AlbumFoldersTreeResponse,
    ApiErrorResponse,
)
from pixelpast.api.services.album_navigation import AlbumNavigationQueryService
from pixelpast.persistence.repositories.album_navigation_read import (
    AlbumNavigationReadRepository,
    AlbumQueryFilters,
)

router = APIRouter(tags=["album"])

ALBUM_FOLDERS_TREE_EXAMPLES = {
    "photo_import_folders": {
        "summary": "Physical folder tree with filtered aggregate counts",
        "value": {
            "supported_filters": ["person_ids", "tag_paths", "filename_query"],
            "applied_filters": {
                "person_ids": [7],
                "tag_paths": ["travel/italy"],
                "filename_query": "IMG_1042",
            },
            "nodes": [
                {
                    "id": 1,
                    "source_id": 2,
                    "source_name": "Photos",
                    "source_type": "photos",
                    "parent_id": None,
                    "name": "photos",
                    "path": "photos",
                    "child_count": 2,
                    "asset_count": 6,
                },
                {
                    "id": 3,
                    "source_id": 2,
                    "source_name": "Photos",
                    "source_type": "photos",
                    "parent_id": 1,
                    "name": "Italy",
                    "path": "photos/Italy",
                    "child_count": 0,
                    "asset_count": 4,
                },
            ],
        },
    }
}

ALBUM_COLLECTIONS_TREE_EXAMPLES = {
    "lightroom_collections": {
        "summary": "Semantic collection tree with filtered aggregate counts",
        "value": {
            "supported_filters": ["person_ids", "tag_paths", "filename_query"],
            "applied_filters": {
                "person_ids": [],
                "tag_paths": ["travel"],
                "filename_query": None,
            },
            "nodes": [
                {
                    "id": 9,
                    "source_id": 4,
                    "source_name": "Lightroom",
                    "source_type": "lightroom_catalog",
                    "parent_id": None,
                    "name": "Trips",
                    "path": "Trips",
                    "collection_type": "collection",
                    "child_count": 1,
                    "asset_count": 12,
                }
            ],
        },
    }
}

ALBUM_ASSET_LISTING_EXAMPLES = {
    "folder_thumbnail_grid": {
        "summary": "Thumbnail-oriented album asset listing",
        "value": {
            "supported_filters": ["person_ids", "tag_paths", "filename_query"],
            "applied_filters": {
                "person_ids": [7],
                "tag_paths": ["travel/italy"],
                "filename_query": None,
            },
            "selection": {
                "node_kind": "folder",
                "id": 3,
                "source_id": 2,
                "source_name": "Photos",
                "source_type": "photos",
                "parent_id": 1,
                "name": "Italy",
                "path": "photos/Italy",
                "asset_count": 2,
                "collection_type": None,
            },
            "items": [
                {
                    "id": 41,
                    "short_id": "PHOTO041",
                    "timestamp": "2024-07-15T18:42:00+00:00",
                    "media_type": "photo",
                    "title": "IMG_1042.JPG",
                    "thumbnail_url": "/media/q200/PHOTO041.webp",
                }
            ],
        },
    }
}

ALBUM_ASSET_DETAIL_EXAMPLES = {
    "selected_photo_detail": {
        "summary": "Lazy-loaded single-photo detail payload",
        "value": {
            "id": 41,
            "short_id": "PHOTO041",
            "source_id": 4,
            "source_name": "Lightroom",
            "source_type": "lightroom_catalog",
            "media_type": "photo",
            "title": "IMG_1042.JPG",
            "caption": "Evening light over the canal.",
            "description": None,
            "timestamp": "2024-07-15T18:42:00+00:00",
            "latitude": 45.4371,
            "longitude": 12.3326,
            "camera": "Canon EOS R5",
            "lens": "RF24-70mm F2.8 L IS USM",
            "aperture_f_number": 2.8,
            "shutter_speed_seconds": 0.005,
            "focal_length_mm": 35.0,
            "iso": 400,
            "thumbnail_url": "/media/q200/PHOTO041.webp",
            "original_url": "/media/orig/PHOTO041",
            "tags": [
                {"id": 12, "label": "Italy", "path": "travel/italy"},
                {"id": 20, "label": "Canal", "path": "places/venice/canal"},
            ],
            "people": [
                {"id": 7, "name": "Anna Becker", "path": "family/anna"},
            ],
            "face_regions": [
                {
                    "name": "Anna Becker",
                    "left": 0.24,
                    "top": 0.18,
                    "right": 0.41,
                    "bottom": 0.46,
                }
            ],
        },
    }
}

ALBUM_BAD_REQUEST_EXAMPLES = {
    **BAD_REQUEST_RESPONSE[400]["content"]["application/json"]["examples"],
    "unsupported_filters": {
        "summary": "Album routes reject unsupported global filters",
        "value": {
            "detail": (
                "unsupported album filters: distance_latitude, location_geometry; "
                "supported filters: person_ids, tag_paths, filename_query"
            )
        },
    },
}

ALBUM_NOT_FOUND_RESPONSES = {
    404: {
        "model": ApiErrorResponse,
        "description": "The requested folder or collection node does not exist.",
        "content": {
            "application/json": {
                "examples": {
                    "unknown_folder": {
                        "summary": "Unknown folder selection",
                        "value": {"detail": "album folder 999 does not exist"},
                    },
                    "unknown_collection": {
                        "summary": "Unknown collection selection",
                        "value": {"detail": "album collection 999 does not exist"},
                    },
                }
            }
        },
    }
}

ALBUM_ASSET_NOT_FOUND_RESPONSES = {
    404: {
        "model": ApiErrorResponse,
        "description": "The requested asset does not exist.",
        "content": {
            "application/json": {
                "examples": {
                    "unknown_asset": {
                        "summary": "Unknown selected asset",
                        "value": {"detail": "album asset 999 does not exist"},
                    }
                }
            }
        },
    }
}


@router.get(
    "/albums/folders",
    response_model=AlbumFoldersTreeResponse,
    summary="Get album folder tree",
    description=(
        "Return the physical album folder tree with filtered descendant asset "
        "counts. The contract keeps source-owned folders explicit and does not "
        "collapse them into the semantic collections tree."
    ),
    response_description="Physical folder navigation tree for the photo-album view.",
    responses=combine_responses(
        {
            200: {
                "content": {
                    "application/json": {
                        "examples": ALBUM_FOLDERS_TREE_EXAMPLES,
                    }
                }
            }
        },
        {
            400: {
                **BAD_REQUEST_RESPONSE[400],
                "content": {
                    "application/json": {
                        "examples": ALBUM_BAD_REQUEST_EXAMPLES,
                    }
                },
            }
        },
        VALIDATION_ERROR_RESPONSE,
    ),
)
def get_album_folder_tree(
    person_ids: list[int] = Query(
        default=[],
        description=(
            "Repeatable person identifiers. Matching assets contribute to node "
            "counts only when linked to at least one selected person."
        ),
    ),
    tag_paths: list[str] = Query(
        default=[],
        description=(
            "Repeatable normalized tag paths used to constrain descendant asset "
            "counts and later thumbnail listings."
        ),
    ),
    location_geometry: str | None = Query(
        default=None,
        description=(
            "Present for global filter consistency, but album tree routes reject "
            "geometry filtering in this increment."
        ),
    ),
    distance_latitude: float | None = Query(
        default=None,
        ge=-90,
        le=90,
        description="Present for global filter consistency, but rejected here.",
    ),
    distance_longitude: float | None = Query(
        default=None,
        ge=-180,
        le=180,
        description="Present for global filter consistency, but rejected here.",
    ),
    distance_radius_meters: int | None = Query(
        default=None,
        ge=1,
        description="Present for global filter consistency, but rejected here.",
    ),
    filename_query: str | None = Query(
        default=None,
        min_length=1,
        description="Case-insensitive filename substring applied to matching assets.",
    ),
    session: Session = Depends(get_db_session),
) -> AlbumFoldersTreeResponse:
    """Return the explicit folder tree for photo-album navigation."""

    filters = _build_album_filters(
        person_ids=person_ids,
        tag_paths=tag_paths,
        location_geometry=location_geometry,
        distance_latitude=distance_latitude,
        distance_longitude=distance_longitude,
        distance_radius_meters=distance_radius_meters,
        filename_query=filename_query,
    )
    return _build_service(session).get_folder_tree(filters=filters)


@router.get(
    "/albums/collections",
    response_model=AlbumCollectionsTreeResponse,
    summary="Get album collection tree",
    description=(
        "Return the semantic album collection tree with filtered aggregate asset "
        "counts. The contract keeps Lightroom-style collections distinct from "
        "physical folders."
    ),
    response_description="Semantic collection navigation tree for the photo-album view.",
    responses=combine_responses(
        {
            200: {
                "content": {
                    "application/json": {
                        "examples": ALBUM_COLLECTIONS_TREE_EXAMPLES,
                    }
                }
            }
        },
        {
            400: {
                **BAD_REQUEST_RESPONSE[400],
                "content": {
                    "application/json": {
                        "examples": ALBUM_BAD_REQUEST_EXAMPLES,
                    }
                },
            }
        },
        VALIDATION_ERROR_RESPONSE,
    ),
)
def get_album_collection_tree(
    person_ids: list[int] = Query(default=[]),
    tag_paths: list[str] = Query(default=[]),
    location_geometry: str | None = Query(default=None),
    distance_latitude: float | None = Query(default=None, ge=-90, le=90),
    distance_longitude: float | None = Query(default=None, ge=-180, le=180),
    distance_radius_meters: int | None = Query(default=None, ge=1),
    filename_query: str | None = Query(default=None, min_length=1),
    session: Session = Depends(get_db_session),
) -> AlbumCollectionsTreeResponse:
    """Return the explicit collection tree for photo-album navigation."""

    filters = _build_album_filters(
        person_ids=person_ids,
        tag_paths=tag_paths,
        location_geometry=location_geometry,
        distance_latitude=distance_latitude,
        distance_longitude=distance_longitude,
        distance_radius_meters=distance_radius_meters,
        filename_query=filename_query,
    )
    return _build_service(session).get_collection_tree(filters=filters)


@router.get(
    "/albums/folders/{folder_id}/assets",
    response_model=AlbumAssetListingResponse,
    response_model_exclude_none=True,
    summary="Get album folder asset listing",
    description=(
        "Return the thumbnail-grid asset listing for one selected physical folder. "
        "Parent folders aggregate descendant assets into one stable browsing result."
    ),
    response_description="Thumbnail-oriented asset listing for one folder selection.",
    responses=combine_responses(
        {
            200: {
                "content": {
                    "application/json": {
                        "examples": ALBUM_ASSET_LISTING_EXAMPLES,
                    }
                }
            }
        },
        {
            400: {
                **BAD_REQUEST_RESPONSE[400],
                "content": {
                    "application/json": {
                        "examples": ALBUM_BAD_REQUEST_EXAMPLES,
                    }
                },
            }
        },
        ALBUM_NOT_FOUND_RESPONSES,
        VALIDATION_ERROR_RESPONSE,
    ),
)
def get_album_folder_asset_listing(
    folder_id: int,
    person_ids: list[int] = Query(default=[]),
    tag_paths: list[str] = Query(default=[]),
    location_geometry: str | None = Query(default=None),
    distance_latitude: float | None = Query(default=None, ge=-90, le=90),
    distance_longitude: float | None = Query(default=None, ge=-180, le=180),
    distance_radius_meters: int | None = Query(default=None, ge=1),
    filename_query: str | None = Query(default=None, min_length=1),
    session: Session = Depends(get_db_session),
) -> AlbumAssetListingResponse:
    """Return the filtered subtree asset listing for one folder node."""

    filters = _build_album_filters(
        person_ids=person_ids,
        tag_paths=tag_paths,
        location_geometry=location_geometry,
        distance_latitude=distance_latitude,
        distance_longitude=distance_longitude,
        distance_radius_meters=distance_radius_meters,
        filename_query=filename_query,
    )
    response = _build_service(session).get_folder_asset_listing(
        folder_id=folder_id,
        filters=filters,
    )
    if response is None:
        raise HTTPException(status_code=404, detail=f"album folder {folder_id} does not exist")
    return response


@router.get(
    "/albums/collections/{collection_id}/assets",
    response_model=AlbumAssetListingResponse,
    response_model_exclude_none=True,
    summary="Get album collection asset listing",
    description=(
        "Return the thumbnail-grid asset listing for one selected semantic "
        "collection. Parent collections aggregate descendant memberships and "
        "deduplicate assets that appear in multiple nested collections."
    ),
    response_description="Thumbnail-oriented asset listing for one collection selection.",
    responses=combine_responses(
        {
            200: {
                "content": {
                    "application/json": {
                        "examples": ALBUM_ASSET_LISTING_EXAMPLES,
                    }
                }
            }
        },
        {
            400: {
                **BAD_REQUEST_RESPONSE[400],
                "content": {
                    "application/json": {
                        "examples": ALBUM_BAD_REQUEST_EXAMPLES,
                    }
                },
            }
        },
        ALBUM_NOT_FOUND_RESPONSES,
        VALIDATION_ERROR_RESPONSE,
    ),
)
def get_album_collection_asset_listing(
    collection_id: int,
    person_ids: list[int] = Query(default=[]),
    tag_paths: list[str] = Query(default=[]),
    location_geometry: str | None = Query(default=None),
    distance_latitude: float | None = Query(default=None, ge=-90, le=90),
    distance_longitude: float | None = Query(default=None, ge=-180, le=180),
    distance_radius_meters: int | None = Query(default=None, ge=1),
    filename_query: str | None = Query(default=None, min_length=1),
    session: Session = Depends(get_db_session),
) -> AlbumAssetListingResponse:
    """Return the filtered subtree asset listing for one collection node."""

    filters = _build_album_filters(
        person_ids=person_ids,
        tag_paths=tag_paths,
        location_geometry=location_geometry,
        distance_latitude=distance_latitude,
        distance_longitude=distance_longitude,
        distance_radius_meters=distance_radius_meters,
        filename_query=filename_query,
    )
    response = _build_service(session).get_collection_asset_listing(
        collection_id=collection_id,
        filters=filters,
    )
    if response is None:
        raise HTTPException(
            status_code=404,
            detail=f"album collection {collection_id} does not exist",
        )
    return response


@router.get(
    "/albums/assets/{asset_id}",
    response_model=AlbumAssetDetailResponse,
    summary="Get album asset detail",
    description=(
        "Return the lazy-loaded single-photo detail payload for one selected asset. "
        "This contract keeps heavier metadata, linked tags and people, and named "
        "face-region overlays off the thumbnail-grid hot path."
    ),
    response_description="Normalized detail payload for one selected album asset.",
    responses=combine_responses(
        {
            200: {
                "content": {
                    "application/json": {
                        "examples": ALBUM_ASSET_DETAIL_EXAMPLES,
                    }
                }
            }
        },
        ALBUM_ASSET_NOT_FOUND_RESPONSES,
        VALIDATION_ERROR_RESPONSE,
    ),
)
def get_album_asset_detail(
    asset_id: int,
    session: Session = Depends(get_db_session),
) -> AlbumAssetDetailResponse:
    """Return one selected asset detail payload."""

    response = _build_service(session).get_asset_detail(asset_id=asset_id)
    if response is None:
        raise HTTPException(status_code=404, detail=f"album asset {asset_id} does not exist")
    return response


def _build_album_filters(
    *,
    person_ids: list[int],
    tag_paths: list[str],
    location_geometry: str | None,
    distance_latitude: float | None,
    distance_longitude: float | None,
    distance_radius_meters: int | None,
    filename_query: str | None,
) -> AlbumQueryFilters:
    unsupported_filters: list[str] = []
    if location_geometry is not None:
        unsupported_filters.append("location_geometry")
    if distance_latitude is not None:
        unsupported_filters.append("distance_latitude")
    if distance_longitude is not None:
        unsupported_filters.append("distance_longitude")
    if distance_radius_meters is not None:
        unsupported_filters.append("distance_radius_meters")

    if unsupported_filters:
        raise HTTPException(
            status_code=400,
            detail=(
                "unsupported album filters: "
                + ", ".join(sorted(unsupported_filters))
                + "; supported filters: person_ids, tag_paths, filename_query"
            ),
        )

    return AlbumQueryFilters(
        person_ids=tuple(sorted(set(person_ids))),
        tag_paths=tuple(sorted(set(tag_paths))),
        filename_query=filename_query.strip() if filename_query is not None else None,
    )


def _build_service(session: Session) -> AlbumNavigationQueryService:
    return AlbumNavigationQueryService(
        repository=AlbumNavigationReadRepository(session),
    )
