"""Contract tests for public OpenAPI route metadata."""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from pixelpast.api.app import create_app
from pixelpast.shared.settings import Settings


def test_public_routes_expose_stable_openapi_tags() -> None:
    schema = _build_openapi_schema()

    assert schema["tags"] == [
        {
            "name": "health",
            "description": "Operational liveness endpoints for local process checks.",
        },
        {
            "name": "album",
            "description": (
                "Photo-album folder trees, collection trees, and asset listings."
            ),
        },
        {
            "name": "timeline",
            "description": (
                "Timeline exploration, day context preload, and day detail reads."
            ),
        },
        {
            "name": "social",
            "description": (
                "Person relationship projections derived from canonical assets."
            ),
        },
        {
            "name": "manage-data",
            "description": (
                "Manual catalog maintenance for canonical persons and groups."
            ),
        },
        {
            "name": "media",
            "description": (
                "Short-id-based thumbnail and original-file delivery for canonical "
                "media assets."
            ),
        },
    ]


def test_album_routes_document_navigation_and_listing_contracts() -> None:
    schema = _build_openapi_schema()
    folders_operation = schema["paths"]["/api/albums/folders"]["get"]
    collections_operation = schema["paths"]["/api/albums/collections"]["get"]
    folder_assets_operation = schema["paths"]["/api/albums/folders/{folder_id}/assets"][
        "get"
    ]
    collection_assets_operation = schema["paths"][
        "/api/albums/collections/{collection_id}/assets"
    ]["get"]

    assert folders_operation["tags"] == ["album"]
    assert folders_operation["summary"] == "Get album folder tree"
    assert folders_operation["responses"]["200"]["description"] == (
        "Physical folder navigation tree for the photo-album view."
    )
    assert "photo_import_folders" in _response_examples(folders_operation, 200)
    assert "unsupported_filters" in _response_examples(folders_operation, 400)

    folder_parameters = _parameters_by_name(folders_operation)
    assert "Repeatable person identifiers" in folder_parameters["person_ids"]["description"]
    assert "geometry filtering" in folder_parameters["location_geometry"]["description"]
    assert _non_null_schema(folder_parameters["distance_latitude"])["minimum"] == -90
    assert _non_null_schema(folder_parameters["filename_query"])["minLength"] == 1

    assert collections_operation["summary"] == "Get album collection tree"
    assert "lightroom_collections" in _response_examples(collections_operation, 200)

    assert folder_assets_operation["summary"] == "Get album folder asset listing"
    assert "folder_thumbnail_grid" in _response_examples(folder_assets_operation, 200)
    assert folder_assets_operation["responses"]["404"]["description"] == (
        "The requested folder or collection node does not exist."
    )

    assert collection_assets_operation["summary"] == "Get album collection asset listing"
    assert "deduplicate assets" in collection_assets_operation["description"]


def test_health_route_exposes_meaningful_openapi_metadata() -> None:
    schema = _build_openapi_schema()
    operation = schema["paths"]["/api/health"]["get"]

    assert operation["tags"] == ["health"]
    assert operation["summary"] == "Check API process health"
    assert "lightweight liveness payload" in operation["description"]
    assert operation["responses"]["200"]["description"] == (
        "Minimal liveness status for the running API process."
    )
    assert "ok" in _response_examples(operation, 200)


def test_exploration_routes_document_contract_metadata_and_errors() -> None:
    schema = _build_openapi_schema()
    bootstrap_operation = schema["paths"]["/api/exploration/bootstrap"]["get"]
    grid_operation = schema["paths"]["/api/exploration"]["get"]

    assert bootstrap_operation["summary"] == "Get exploration bootstrap metadata"
    assert bootstrap_operation["tags"] == ["timeline"]
    assert bootstrap_operation["responses"]["400"]["description"].startswith(
        "The request was syntactically valid"
    )
    assert bootstrap_operation["responses"]["422"]["description"].startswith(
        "The request could not be parsed"
    )
    assert _parameters_by_name(bootstrap_operation)["start"]["description"].startswith(
        "Inclusive UTC start date"
    )
    assert _parameters_by_name(bootstrap_operation)["end"]["description"].startswith(
        "Inclusive UTC end date"
    )
    assert "winter_overview" in _response_examples(bootstrap_operation, 200)
    assert "partial_range" in _response_examples(bootstrap_operation, 400)
    assert "invalid_date" in _response_examples(bootstrap_operation, 422)
    assert "winter_window" in _parameter_examples(
        _parameters_by_name(bootstrap_operation)["start"]
    )

    grid_parameters = _parameters_by_name(grid_operation)
    assert grid_operation["summary"] == "Get exploration day grid"
    assert grid_operation["responses"]["200"]["description"] == (
        "Dense exploration grid for the resolved UTC date range."
    )
    assert _non_null_schema(grid_parameters["distance_latitude"])["minimum"] == -90
    assert _non_null_schema(grid_parameters["distance_latitude"])["maximum"] == 90
    assert _non_null_schema(grid_parameters["distance_longitude"])["minimum"] == -180
    assert _non_null_schema(grid_parameters["distance_longitude"])["maximum"] == 180
    assert _non_null_schema(grid_parameters["distance_radius_meters"])["minimum"] == 1
    assert _non_null_schema(grid_parameters["filename_query"])["minLength"] == 1
    assert "daily view identifier" in grid_parameters["view_mode"]["description"]
    assert "Repeatable person identifiers" in (
        grid_parameters["person_ids"]["description"]
    )
    assert "filtered_travel_grid" in _response_examples(grid_operation, 200)
    assert "trip_window_start" in _parameter_examples(grid_parameters["start"])
    assert "anna" in _parameter_examples(grid_parameters["person_ids"])
    assert "venice" in _parameter_examples(grid_parameters["tag_paths"])


def test_day_routes_document_parameter_semantics_and_errors() -> None:
    schema = _build_openapi_schema()
    context_operation = schema["paths"]["/api/days/context"]["get"]
    detail_operation = schema["paths"]["/api/days/{day}"]["get"]

    context_parameters = _parameters_by_name(context_operation)
    assert context_operation["summary"] == "Get day context preload"
    assert context_operation["responses"]["400"]["description"].startswith(
        "The request was syntactically valid"
    )
    assert context_parameters["start"]["required"] is True
    assert context_parameters["end"]["required"] is True
    assert "context preload" in context_parameters["start"]["description"]
    assert _non_null_schema(context_parameters["filename_query"])["minLength"] == 1
    assert "preloaded_trip_week" in _response_examples(context_operation, 200)
    assert "window_limit" in _response_examples(context_operation, 400)
    assert "trip_window_start" in _parameter_examples(context_parameters["start"])
    assert "travel_tag" in _parameter_examples(context_parameters["tag_paths"])

    detail_parameters = _parameters_by_name(detail_operation)
    assert detail_operation["summary"] == "Get one day timeline"
    assert detail_operation["responses"]["422"]["description"].startswith(
        "The request could not be parsed"
    )
    assert detail_parameters["day"]["required"] is True
    assert detail_parameters["day"]["description"] == (
        "UTC calendar day to inspect in ISO format (YYYY-MM-DD)."
    )
    assert "mixed_day_timeline" in _response_examples(detail_operation, 200)
    assert "invalid_path_date" in _response_examples(detail_operation, 422)
    assert "summer_day" in _parameter_examples(detail_parameters["day"])


def test_social_graph_route_documents_supported_and_rejected_filters() -> None:
    schema = _build_openapi_schema()
    operation = schema["paths"]["/api/social/graph"]["get"]
    parameters = _parameters_by_name(operation)

    assert operation["summary"] == "Get social graph projection"
    assert operation["tags"] == ["social"]
    assert operation["responses"]["400"]["description"].startswith(
        "The request was syntactically valid"
    )
    assert parameters["max_people_per_asset"]["schema"]["minimum"] == 2
    assert parameters["max_people_per_asset"]["schema"]["maximum"] == 30
    assert "seed person identifiers" in parameters["person_ids"]["description"]
    assert "rejects tag-based filtering" in parameters["tag_paths"]["description"]
    assert "rejects filename-based filtering" in (
        parameters["filename_query"]["description"]
    )
    assert "trip_companions" in _response_examples(operation, 200)
    assert "unsupported_filters" in _response_examples(operation, 400)
    assert "anna" in _parameter_examples(parameters["person_ids"])
    assert "unsupported_tag" in _parameter_examples(parameters["tag_paths"])


def test_manage_data_routes_document_catalog_contracts() -> None:
    schema = _build_openapi_schema()
    persons_get = schema["paths"]["/api/manage-data/persons"]["get"]
    persons_put = schema["paths"]["/api/manage-data/persons"]["put"]
    groups_get = schema["paths"]["/api/manage-data/person-groups"]["get"]
    groups_put = schema["paths"]["/api/manage-data/person-groups"]["put"]
    membership_get = schema["paths"][
        "/api/manage-data/person-groups/{group_id}/members"
    ]["get"]
    membership_put = schema["paths"][
        "/api/manage-data/person-groups/{group_id}/members"
    ]["put"]

    assert persons_get["tags"] == ["manage-data"]
    assert persons_get["summary"] == "Get persons catalog"
    assert persons_get["responses"]["200"]["description"] == (
        "Canonical persons catalog for manual maintenance."
    )
    assert "family_catalog" in _response_examples(persons_get, 200)

    assert persons_put["summary"] == "Save persons catalog draft"
    assert persons_put["responses"]["400"]["description"].startswith(
        "The request was syntactically valid"
    )
    assert "upsert_people" in _request_examples(persons_put)
    assert "person_delete_forbidden" in _response_examples(persons_put, 400)

    assert groups_get["tags"] == ["manage-data"]
    assert groups_get["summary"] == "Get person-group catalog"
    assert "managed_groups" in _response_examples(groups_get, 200)

    assert groups_put["summary"] == "Save person-group catalog draft"
    assert "replace_groups" in _request_examples(groups_put)
    assert groups_put["responses"]["200"]["description"] == (
        "Reloaded canonical person-group catalog after persistence."
    )

    assert membership_get["summary"] == "Get one person-group membership set"
    assert "loaded_membership" in _response_examples(membership_get, 200)
    assert membership_put["summary"] == "Save one person-group membership draft"
    assert "replace_membership" in _request_examples(membership_put)
    assert membership_put["responses"]["200"]["description"] == (
        "Reloaded person-group membership state after persistence."
    )


def test_media_routes_document_media_delivery_contract() -> None:
    schema = _build_openapi_schema()
    h120_operation = schema["paths"]["/media/h120/{short_id}.webp"]["get"]
    h240_operation = schema["paths"]["/media/h240/{short_id}.webp"]["get"]
    q200_operation = schema["paths"]["/media/q200/{short_id}.webp"]["get"]
    original_operation = schema["paths"]["/media/orig/{short_id}"]["get"]

    assert h120_operation["tags"] == ["media"]
    assert h120_operation["summary"] == "Get h120 WebP thumbnail"
    assert h120_operation["responses"]["200"]["description"] == (
        "Fixed WebP thumbnail for the requested asset short id."
    )
    assert "image/webp" in h120_operation["responses"]["200"]["content"]
    assert "cached_h120" in h120_operation["responses"]["200"]["content"]["image/webp"][
        "examples"
    ]
    assert "unknown_short_id" in _response_examples(h120_operation, 404)
    assert "unsupported_asset" in _response_examples(h120_operation, 415)
    assert "canonical database lookup" in h120_operation["description"]

    assert h240_operation["summary"] == "Get h240 WebP thumbnail"
    assert q200_operation["summary"] == "Get q200 WebP thumbnail"
    assert original_operation["summary"] == "Get original media file"
    assert original_operation["tags"] == ["media"]
    assert original_operation["responses"]["200"]["description"] == (
        "Original media file resolved from canonical asset provenance for the "
        "requested asset short id."
    )
    assert "Content-Disposition" in original_operation["responses"]["200"]["headers"]
    assert "jpeg_inline" in (
        original_operation["responses"]["200"]["content"]["image/*"]["examples"]
    )
    assert "unknown_short_id" in _response_examples(original_operation, 404)
    assert "unresolved_original_path" in _response_examples(original_operation, 404)
    assert "canonical asset through the database" in original_operation["description"]


def _build_openapi_schema() -> dict[str, object]:
    workspace_root = _create_workspace_dir(prefix="openapi-route-metadata")
    try:
        database_path = workspace_root / "pixelpast.db"
        settings = Settings(database_url=f"sqlite:///{database_path.as_posix()}")
        app = create_app(settings=settings)
        try:
            return app.openapi()
        finally:
            app.state.engine.dispose()
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def _parameters_by_name(operation: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        parameter["name"]: parameter
        for parameter in operation.get("parameters", [])
        if isinstance(parameter, dict) and "name" in parameter
    }


def _response_examples(
    operation: dict[str, object],
    status_code: int,
) -> dict[str, object]:
    return (
        operation["responses"][str(status_code)]["content"]["application/json"].get(
            "examples", {}
        )
    )


def _parameter_examples(parameter: dict[str, object]) -> dict[str, object]:
    return parameter.get("examples", {})


def _request_examples(operation: dict[str, object]) -> dict[str, object]:
    return operation["requestBody"]["content"]["application/json"].get("examples", {})


def _non_null_schema(parameter: dict[str, object]) -> dict[str, object]:
    schema = parameter["schema"]
    if "anyOf" not in schema:
        return schema

    return next(
        nested_schema
        for nested_schema in schema["anyOf"]
        if isinstance(nested_schema, dict) and nested_schema.get("type") != "null"
    )


def _create_workspace_dir(*, prefix: str) -> Path:
    workspace_root = Path("var") / f"{prefix}-{uuid4().hex}"
    workspace_root.mkdir(parents=True, exist_ok=False)
    return workspace_root
