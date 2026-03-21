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
            "name": "timeline",
            "description": "Timeline exploration, day context preload, and day detail reads.",
        },
        {
            "name": "social",
            "description": "Person relationship projections derived from canonical assets.",
        },
    ]


def test_health_route_exposes_meaningful_openapi_metadata() -> None:
    schema = _build_openapi_schema()
    operation = schema["paths"]["/api/health"]["get"]

    assert operation["tags"] == ["health"]
    assert operation["summary"] == "Check API process health"
    assert "lightweight liveness payload" in operation["description"]
    assert operation["responses"]["200"]["description"] == (
        "Minimal liveness status for the running API process."
    )


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
    assert "Repeatable person identifiers" in grid_parameters["person_ids"]["description"]


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

    detail_parameters = _parameters_by_name(detail_operation)
    assert detail_operation["summary"] == "Get one day timeline"
    assert detail_operation["responses"]["422"]["description"].startswith(
        "The request could not be parsed"
    )
    assert detail_parameters["day"]["required"] is True
    assert detail_parameters["day"]["description"] == (
        "UTC calendar day to inspect in ISO format (YYYY-MM-DD)."
    )


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
    assert "rejects filename-based filtering" in parameters["filename_query"]["description"]


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
