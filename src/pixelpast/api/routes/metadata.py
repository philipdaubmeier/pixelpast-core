"""Shared OpenAPI metadata for public API routes."""

from __future__ import annotations

from typing import Any

from pixelpast.api.schemas.errors import (
    ApiErrorResponse,
    ApiValidationErrorResponse,
)

OPENAPI_TAGS = [
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

BAD_REQUEST_RESPONSE: dict[int, dict[str, Any]] = {
    400: {
        "model": ApiErrorResponse,
        "description": (
            "The request was syntactically valid but violated a documented "
            "PixelPast API contract constraint."
        ),
    }
}

VALIDATION_ERROR_RESPONSE: dict[int, dict[str, Any]] = {
    422: {
        "model": ApiValidationErrorResponse,
        "description": (
            "The request could not be parsed or failed declared parameter "
            "validation."
        ),
    }
}


def combine_responses(
    *response_groups: dict[int, dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    """Merge reusable response metadata blocks for one route declaration."""

    combined: dict[int, dict[str, Any]] = {}
    for response_group in response_groups:
        combined.update(response_group)
    return combined
