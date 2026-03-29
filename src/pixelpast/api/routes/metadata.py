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
    {
        "name": "manage-data",
        "description": "Manual catalog maintenance for canonical persons and groups.",
    },
]

BAD_REQUEST_EXAMPLES = {
    "invalid_range": {
        "summary": "Start date after end date",
        "value": {"detail": "start must be less than or equal to end"},
    },
    "partial_range": {
        "summary": "Only one range boundary provided",
        "value": {"detail": "start and end must both be provided together"},
    },
}

VALIDATION_ERROR_EXAMPLES = {
    "invalid_date": {
        "summary": "Unparseable ISO date",
        "value": {
            "detail": [
                {
                    "type": "date_from_datetime_parsing",
                    "loc": ["query", "start"],
                    "msg": "Input should be a valid date or datetime, input is too short",
                    "input": "2026-02",
                }
            ]
        },
    },
    "invalid_path_date": {
        "summary": "Invalid path day format",
        "value": {
            "detail": [
                {
                    "type": "date_from_datetime_parsing",
                    "loc": ["path", "day"],
                    "msg": "Input should be a valid date or datetime, invalid date separator",
                    "input": "2026/07/14",
                }
            ]
        },
    },
}

BAD_REQUEST_RESPONSE: dict[int, dict[str, Any]] = {
    400: {
        "model": ApiErrorResponse,
        "description": (
            "The request was syntactically valid but violated a documented "
            "PixelPast API contract constraint."
        ),
        "content": {
            "application/json": {
                "examples": BAD_REQUEST_EXAMPLES,
            }
        },
    }
}

VALIDATION_ERROR_RESPONSE: dict[int, dict[str, Any]] = {
    422: {
        "model": ApiValidationErrorResponse,
        "description": (
            "The request could not be parsed or failed declared parameter "
            "validation."
        ),
        "content": {
            "application/json": {
                "examples": VALIDATION_ERROR_EXAMPLES,
            }
        },
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
