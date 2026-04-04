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
    AlbumContextResponse,
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
        "summary": "Physical folder tree with structural aggregate counts",
        "value": {
            "supported_filters": ["person_group_ids"],
            "applied_filters": {
                "person_group_ids": [3],
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
                    "person_groups": [
                        {
                            "group_id": 3,
                            "group_name": "Family",
                            "color_index": 2,
                            "matched_person_count": 4,
                            "group_person_count": 5,
                            "matched_asset_count": 6,
                            "matched_creator_person_count": 2,
                        }
                    ],
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
                    "person_groups": [
                        {
                            "group_id": 3,
                            "group_name": "Family",
                            "color_index": 2,
                            "matched_person_count": 2,
                            "group_person_count": 5,
                            "matched_asset_count": 4,
                            "matched_creator_person_count": 1,
                        }
                    ],
                },
            ],
        },
    }
}

ALBUM_COLLECTIONS_TREE_EXAMPLES = {
    "lightroom_collections": {
        "summary": "Semantic collection tree with structural aggregate counts",
        "value": {
            "supported_filters": ["person_group_ids"],
            "applied_filters": {
                "person_group_ids": [5],
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
                    "person_groups": [
                        {
                            "group_id": 5,
                            "group_name": "Friends",
                            "color_index": 4,
                            "matched_person_count": 3,
                            "group_person_count": 4,
                            "matched_asset_count": 12,
                            "matched_creator_person_count": 1,
                        }
                    ],
                }
            ],
        },
    }
}

ALBUM_ASSET_LISTING_EXAMPLES = {
    "folder_thumbnail_grid": {
        "summary": "Thumbnail-oriented album asset listing",
        "value": {
            "supported_filters": ["person_ids", "tag_paths"],
            "applied_filters": {
                "person_ids": [7],
                "tag_paths": ["travel/italy"],
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

ALBUM_CONTEXT_EXAMPLES = {
    "folder_stable_context": {
        "summary": "Stable album context with per-asset hover highlights",
        "value": {
            "supported_filters": ["person_ids", "tag_paths"],
            "applied_filters": {
                "person_ids": [1],
                "tag_paths": ["travel/italy"],
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
            "person_groups": [
                {
                    "group_id": 3,
                    "group_name": "Family",
                    "color_index": 2,
                    "matched_person_count": 2,
                    "group_person_count": 5,
                    "matched_asset_count": 2,
                    "matched_creator_person_count": 1,
                }
            ],
            "persons": [
                {
                    "id": 7,
                    "name": "Anna Becker",
                    "path": "family/anna",
                    "asset_count": 2,
                }
            ],
            "tags": [
                {
                    "id": 12,
                    "label": "Italy",
                    "path": "travel/italy",
                    "asset_count": 2,
                }
            ],
            "map_points": [
                {
                    "id": "asset:PHOTO041",
                    "label": "Venice",
                    "latitude": 45.4371,
                    "longitude": 12.3326,
                    "asset_count": 1,
                }
            ],
            "asset_contexts": [
                {
                    "asset_id": 41,
                    "person_ids": [7],
                    "tag_paths": ["travel/italy"],
                    "map_point_ids": ["asset:PHOTO041"],
                }
            ],
            "summary_counts": {
                "assets": 2,
                "people": 1,
                "tags": 1,
                "places": 1,
            },
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
            "creator": "Anna Becker",
            "preserved_filename": "IMG_1042.CR3",
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
        "summary": "Album routes reject unsupported filters for each read shape",
        "value": {
            "detail": (
                "unsupported album filters: distance_latitude, location_geometry; "
                "supported filters: person_ids, tag_paths"
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
        "Return the physical album folder tree with structural descendant asset "
        "counts. Only person-group filtering affects tree visibility; other "
        "album filters stay local to the selected node."
    ),
    response_model_exclude_none=True,
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
            "Present for cross-view filter consistency, but album tree routes "
            "reject person filtering in this increment."
        ),
    ),
    person_group_ids: list[int] = Query(
        default=[],
        description=(
            "Repeatable person-group identifiers. Folder nodes remain visible "
            "only when they carry derived relevance for at least one selected group."
        ),
    ),
    tag_paths: list[str] = Query(
        default=[],
        description=(
            "Present for cross-view filter consistency, but album tree routes "
            "reject tag filtering in this increment."
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
        description="Present for cross-view filter consistency, but rejected here.",
    ),
    session: Session = Depends(get_db_session),
) -> AlbumFoldersTreeResponse:
    """Return the explicit folder tree for photo-album navigation."""

    filters = _build_tree_filters(
        person_ids=person_ids,
        person_group_ids=person_group_ids,
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
        "Return the semantic album collection tree with structural aggregate "
        "asset counts. Only person-group filtering affects tree visibility; "
        "other album filters stay local to the selected node."
    ),
    response_model_exclude_none=True,
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
    person_ids: list[int] = Query(
        default=[],
        description="Present for cross-view filter consistency, but rejected here.",
    ),
    person_group_ids: list[int] = Query(
        default=[],
        description=(
            "Repeatable person-group identifiers. Collection nodes remain visible "
            "only when they carry derived relevance for at least one selected group."
        ),
    ),
    tag_paths: list[str] = Query(
        default=[],
        description="Present for cross-view filter consistency, but rejected here.",
    ),
    location_geometry: str | None = Query(
        default=None,
        description="Present for cross-view filter consistency, but rejected here.",
    ),
    distance_latitude: float | None = Query(
        default=None,
        ge=-90,
        le=90,
        description="Present for cross-view filter consistency, but rejected here.",
    ),
    distance_longitude: float | None = Query(
        default=None,
        ge=-180,
        le=180,
        description="Present for cross-view filter consistency, but rejected here.",
    ),
    distance_radius_meters: int | None = Query(
        default=None,
        ge=1,
        description="Present for cross-view filter consistency, but rejected here.",
    ),
    filename_query: str | None = Query(
        default=None,
        min_length=1,
        description="Present for cross-view filter consistency, but rejected here.",
    ),
    session: Session = Depends(get_db_session),
) -> AlbumCollectionsTreeResponse:
    """Return the explicit collection tree for photo-album navigation."""

    filters = _build_tree_filters(
        person_ids=person_ids,
        person_group_ids=person_group_ids,
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
    person_group_ids: list[int] = Query(
        default=[],
        description="Present for tree navigation consistency, but rejected here.",
    ),
    location_geometry: str | None = Query(default=None),
    distance_latitude: float | None = Query(default=None, ge=-90, le=90),
    distance_longitude: float | None = Query(default=None, ge=-180, le=180),
    distance_radius_meters: int | None = Query(default=None, ge=1),
    filename_query: str | None = Query(
        default=None,
        min_length=1,
        description="Present for cross-view filter consistency, but rejected here.",
    ),
    session: Session = Depends(get_db_session),
) -> AlbumAssetListingResponse:
    """Return the filtered subtree asset listing for one folder node."""

    filters = _build_selection_filters(
        person_ids=person_ids,
        person_group_ids=person_group_ids,
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
    "/albums/folders/{folder_id}/context",
    response_model=AlbumContextResponse,
    response_model_exclude_none=True,
    summary="Get album folder context",
    description=(
        "Return the stable right-column context for one selected physical folder. "
        "The response includes aggregate people, tags, and map points plus "
        "per-asset lightweight highlight links so thumbnail hover stays local."
    ),
    response_description="Stable album context for one folder selection.",
    responses=combine_responses(
        {
            200: {
                "content": {
                    "application/json": {
                        "examples": ALBUM_CONTEXT_EXAMPLES,
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
def get_album_folder_context(
    folder_id: int,
    person_ids: list[int] = Query(default=[]),
    person_group_ids: list[int] = Query(
        default=[],
        description="Present for tree navigation consistency, but rejected here.",
    ),
    tag_paths: list[str] = Query(default=[]),
    location_geometry: str | None = Query(default=None),
    distance_latitude: float | None = Query(default=None, ge=-90, le=90),
    distance_longitude: float | None = Query(default=None, ge=-180, le=180),
    distance_radius_meters: int | None = Query(default=None, ge=1),
    filename_query: str | None = Query(
        default=None,
        min_length=1,
        description="Present for cross-view filter consistency, but rejected here.",
    ),
    session: Session = Depends(get_db_session),
) -> AlbumContextResponse:
    """Return the stable album context for one folder node."""

    filters = _build_selection_filters(
        person_ids=person_ids,
        person_group_ids=person_group_ids,
        tag_paths=tag_paths,
        location_geometry=location_geometry,
        distance_latitude=distance_latitude,
        distance_longitude=distance_longitude,
        distance_radius_meters=distance_radius_meters,
        filename_query=filename_query,
    )
    response = _build_service(session).get_folder_context(
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
    person_group_ids: list[int] = Query(
        default=[],
        description="Present for tree navigation consistency, but rejected here.",
    ),
    location_geometry: str | None = Query(default=None),
    distance_latitude: float | None = Query(default=None, ge=-90, le=90),
    distance_longitude: float | None = Query(default=None, ge=-180, le=180),
    distance_radius_meters: int | None = Query(default=None, ge=1),
    filename_query: str | None = Query(
        default=None,
        min_length=1,
        description="Present for cross-view filter consistency, but rejected here.",
    ),
    session: Session = Depends(get_db_session),
) -> AlbumAssetListingResponse:
    """Return the filtered subtree asset listing for one collection node."""

    filters = _build_selection_filters(
        person_ids=person_ids,
        person_group_ids=person_group_ids,
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
    "/albums/collections/{collection_id}/context",
    response_model=AlbumContextResponse,
    response_model_exclude_none=True,
    summary="Get album collection context",
    description=(
        "Return the stable right-column context for one selected semantic "
        "collection. Thumbnail hover remains client-side by using the per-asset "
        "lightweight highlight links returned with the aggregate context."
    ),
    response_description="Stable album context for one collection selection.",
    responses=combine_responses(
        {
            200: {
                "content": {
                    "application/json": {
                        "examples": ALBUM_CONTEXT_EXAMPLES,
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
def get_album_collection_context(
    collection_id: int,
    person_ids: list[int] = Query(default=[]),
    person_group_ids: list[int] = Query(
        default=[],
        description="Present for tree navigation consistency, but rejected here.",
    ),
    tag_paths: list[str] = Query(default=[]),
    location_geometry: str | None = Query(default=None),
    distance_latitude: float | None = Query(default=None, ge=-90, le=90),
    distance_longitude: float | None = Query(default=None, ge=-180, le=180),
    distance_radius_meters: int | None = Query(default=None, ge=1),
    filename_query: str | None = Query(
        default=None,
        min_length=1,
        description="Present for cross-view filter consistency, but rejected here.",
    ),
    session: Session = Depends(get_db_session),
) -> AlbumContextResponse:
    """Return the stable album context for one collection node."""

    filters = _build_selection_filters(
        person_ids=person_ids,
        person_group_ids=person_group_ids,
        tag_paths=tag_paths,
        location_geometry=location_geometry,
        distance_latitude=distance_latitude,
        distance_longitude=distance_longitude,
        distance_radius_meters=distance_radius_meters,
        filename_query=filename_query,
    )
    response = _build_service(session).get_collection_context(
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


def _build_tree_filters(
    *,
    person_ids: list[int],
    person_group_ids: list[int],
    tag_paths: list[str],
    location_geometry: str | None,
    distance_latitude: float | None,
    distance_longitude: float | None,
    distance_radius_meters: int | None,
    filename_query: str | None,
) -> AlbumQueryFilters:
    unsupported_filters: list[str] = []
    if person_ids:
        unsupported_filters.append("person_ids")
    if tag_paths:
        unsupported_filters.append("tag_paths")
    if location_geometry is not None:
        unsupported_filters.append("location_geometry")
    if distance_latitude is not None:
        unsupported_filters.append("distance_latitude")
    if distance_longitude is not None:
        unsupported_filters.append("distance_longitude")
    if distance_radius_meters is not None:
        unsupported_filters.append("distance_radius_meters")
    if filename_query is not None:
        unsupported_filters.append("filename_query")

    if unsupported_filters:
        raise HTTPException(
            status_code=400,
            detail=(
                "unsupported album filters: "
                + ", ".join(sorted(unsupported_filters))
                + "; supported filters: person_group_ids"
            ),
        )

    return AlbumQueryFilters(
        person_group_ids=tuple(sorted(set(person_group_ids))),
    )


def _build_selection_filters(
    *,
    person_ids: list[int],
    person_group_ids: list[int] | None = None,
    tag_paths: list[str],
    location_geometry: str | None,
    distance_latitude: float | None,
    distance_longitude: float | None,
    distance_radius_meters: int | None,
    filename_query: str | None,
) -> AlbumQueryFilters:
    unsupported_filters: list[str] = []
    if person_group_ids:
        unsupported_filters.append("person_group_ids")
    if location_geometry is not None:
        unsupported_filters.append("location_geometry")
    if distance_latitude is not None:
        unsupported_filters.append("distance_latitude")
    if distance_longitude is not None:
        unsupported_filters.append("distance_longitude")
    if distance_radius_meters is not None:
        unsupported_filters.append("distance_radius_meters")
    if filename_query is not None:
        unsupported_filters.append("filename_query")

    if unsupported_filters:
        raise HTTPException(
            status_code=400,
            detail=(
                "unsupported album filters: "
                + ", ".join(sorted(unsupported_filters))
                + "; supported filters: person_ids, tag_paths"
            ),
        )

    return AlbumQueryFilters(
        person_ids=tuple(sorted(set(person_ids))),
        tag_paths=tuple(sorted(set(tag_paths))),
    )


def _build_service(session: Session) -> AlbumNavigationQueryService:
    return AlbumNavigationQueryService(
        repository=AlbumNavigationReadRepository(session),
    )
