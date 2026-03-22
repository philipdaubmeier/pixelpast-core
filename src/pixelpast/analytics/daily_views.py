"""Derived-domain metadata for reusable daily exploration views."""

from __future__ import annotations

from dataclasses import dataclass

from pixelpast.persistence.models import (
    DAILY_AGGREGATE_OVERALL_SOURCE_TYPE,
    DAILY_AGGREGATE_SCOPE_OVERALL,
    DAILY_AGGREGATE_SCOPE_SOURCE_TYPE,
)

DEFAULT_ACTIVITY_SCORE_COLOR_THRESHOLDS: tuple[dict[str, object], ...] = (
    {"activity_score": 1, "color_value": "low"},
    {"activity_score": 35, "color_value": "medium"},
    {"activity_score": 70, "color_value": "high"},
)
SPOTIFY_SOURCE_TYPE = "spotify"
TIMELINE_ACTIVITY_SOURCE_TYPE = "timeline_activity"
TIMELINE_VISIT_SOURCE_TYPE = "timeline_visit"
WORKDAYS_VACATION_SOURCE_TYPE = "workdays_vacation"


@dataclass(slots=True, frozen=True)
class DailyView:
    """Derived metadata describing one reusable daily aggregate view."""

    aggregate_scope: str
    source_type: str | None
    label: str
    description: str
    metadata_json: dict[str, object]


def build_default_daily_view_metadata() -> dict[str, object]:
    """Return the default backend-owned metadata for one daily view."""

    return {
        "score_version": "v2",
        "score_formula": "activity_score = total_events + media_count",
        "summary_version": "v1",
        "source_partitioning": "events use source.type; assets use media_type",
        "activity_score_color_thresholds": [
            dict(threshold) for threshold in DEFAULT_ACTIVITY_SCORE_COLOR_THRESHOLDS
        ],
    }


def build_workdays_vacation_daily_view_metadata() -> dict[str, object]:
    """Return metadata for the direct-color workdays-vacation view."""

    metadata = build_default_daily_view_metadata()
    metadata["activity_score_color_thresholds"] = []
    metadata["direct_color"] = True
    return metadata


def build_daily_view(
    *,
    aggregate_scope: str,
    source_type: str,
) -> DailyView:
    """Return deterministic metadata for one daily aggregate identity."""

    if aggregate_scope == DAILY_AGGREGATE_SCOPE_OVERALL:
        return DailyView(
            aggregate_scope=aggregate_scope,
            source_type=None,
            label="Activity",
            description="Default heat intensity across all timeline sources.",
            metadata_json=build_default_daily_view_metadata(),
        )

    if aggregate_scope != DAILY_AGGREGATE_SCOPE_SOURCE_TYPE:
        raise ValueError(f"Unsupported daily view scope: {aggregate_scope}")

    if source_type == DAILY_AGGREGATE_OVERALL_SOURCE_TYPE:
        raise ValueError("Source-scoped daily views require a concrete source type")

    normalized_source_type = source_type.replace("_", " ").strip()
    label = normalized_source_type.title()
    metadata_json = build_default_daily_view_metadata()
    description = f"Highlights days with {normalized_source_type} activity."
    if source_type == SPOTIFY_SOURCE_TYPE:
        label = "Spotify"
        description = "Highlights days with Spotify listening activity."
    if source_type == TIMELINE_VISIT_SOURCE_TYPE:
        label = "Timeline Visits"
        description = "Highlights days with timeline visit activity."
    if source_type == TIMELINE_ACTIVITY_SOURCE_TYPE:
        label = "Timeline Activity"
        description = "Highlights days with timeline movement activity."
    if source_type == WORKDAYS_VACATION_SOURCE_TYPE:
        description = (
            "Highlights days imported from the workdays vacation workbook "
            "using per-day direct colors."
        )
        metadata_json = build_workdays_vacation_daily_view_metadata()
    return DailyView(
        aggregate_scope=aggregate_scope,
        source_type=source_type,
        label=label,
        description=description,
        metadata_json=metadata_json,
    )
